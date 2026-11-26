"""
Builds the Silver tables straight from the parsed XML, the same way the
Fabric Notebook_GetData does (parse_sponsors / parse_cosponsors / ...).

Why: rebuilding these from Bronze.XmlElement / Bronze.XmlValue means
pivoting millions of generic rows in SQL (Silver.BuildCosponsors was the
slow one). Here each file is already parsed into an ElementTree, so we
read the fields directly and bulk insert typed rows. No pivot.

Silver.Bills is still built by Silver.BuildBills (unchanged).
"""

import datetime
import logging

CHUNK_SIZE = 10000


# ============================================================
# HELPERS (same as the Fabric notebook)
# ============================================================

def strip_namespaces(root):
    """GovInfo BILLSTATUS files normally have no namespace, but strip
    any just in case so .find('bill') works."""
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def get(el, *path, default=None):
    node = el
    for step in path:
        if node is None:
            return default
        node = node.find(step)
    if node is None or node.text is None:
        return default
    return node.text.strip() or default


def safe_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def safe_date(val):
    """'2025-01-03' or '2025-01-03T14:22:00Z' -> date. Like TRY_CONVERT(date, ...)."""
    if not val:
        return None
    try:
        return datetime.date.fromisoformat(val[:10])
    except ValueError:
        return None


def trunc(val, length):
    """Mirror the CAST(... AS VARCHAR(n)) in the old procs so long values
    don't fail the insert."""
    if val is None:
        return None
    return val[:length]


# ============================================================
# PARSERS — one per Silver table
# Every row starts with (Type, BillNumber) to match Silver.Bills' key.
# ============================================================

def parse_sponsors(bill, bill_type, bill_number, file_id):
    rows = []
    sponsors = bill.find("sponsors")
    if sponsors is None:
        return rows
    for item in sponsors.findall("item"):
        rows.append((
            bill_type, bill_number,
            trunc(get(item, "bioguideId"), 20),
            trunc(get(item, "fullName"), 300),
            trunc(get(item, "firstName"), 100),
            trunc(get(item, "middleName"), 100),
            trunc(get(item, "lastName"), 100),
            trunc(get(item, "party"), 10),
            trunc(get(item, "state"), 2),
            safe_int(get(item, "district")),
            trunc(get(item, "isByRequest"), 50),
            file_id,
        ))
    return rows


def parse_cosponsors(bill, bill_type, bill_number, file_id):
    rows = []
    cosponsors = bill.find("cosponsors")
    if cosponsors is None:
        return rows
    for item in cosponsors.findall("item"):
        rows.append((
            bill_type, bill_number,
            trunc(get(item, "bioguideId"), 20),
            trunc(get(item, "fullName"), 300),
            trunc(get(item, "firstName"), 100),
            trunc(get(item, "middleName"), 100),
            trunc(get(item, "lastName"), 100),
            trunc(get(item, "party"), 10),
            trunc(get(item, "state"), 2),
            safe_int(get(item, "district")),
            safe_date(get(item, "sponsorshipDate")),
            trunc(get(item, "isOriginalCosponsor"), 5),
            file_id,
        ))
    return rows


def parse_actions(bill, bill_type, bill_number, file_id):
    rows = []
    actions = bill.find("actions")
    if actions is None:
        return rows
    for seq, item in enumerate(actions.findall("item")):
        src = item.find("sourceSystem")
        vote = item.find("recordedVotes")
        vote = vote.find("recordedVote") if vote is not None else None
        rows.append((
            bill_type, bill_number, seq,
            safe_date(get(item, "actionDate")),
            trunc(get(item, "actionTime"), 20),
            trunc(get(item, "actionCode"), 50),
            trunc(get(item, "type"), 100),
            get(item, "text"),
            trunc(get(src, "name"), 200) if src is not None else None,
            trunc(get(src, "code"), 20) if src is not None else None,
            safe_int(get(vote, "rollNumber")) if vote is not None else None,
            trunc(get(vote, "chamber"), 50) if vote is not None else None,
            safe_date(get(vote, "date")) if vote is not None else None,
            trunc(get(vote, "url"), 500) if vote is not None else None,
            file_id,
        ))
    return rows


def parse_subjects(bill, bill_type, bill_number, file_id):
    rows = []
    subjects = bill.find("subjects")
    if subjects is None:
        return rows
    legislative = subjects.find("legislativeSubjects")
    if legislative is not None:
        for item in legislative.findall("item"):
            name = get(item, "name")
            if name:
                rows.append((bill_type, bill_number, "legislativeSubject", trunc(name, 300), file_id))
    policy_area = subjects.find("policyArea")
    if policy_area is not None and get(policy_area, "name"):
        rows.append((bill_type, bill_number, "policyArea", trunc(get(policy_area, "name"), 300), file_id))
    return rows


def dedupe(rows, key_len):
    """Keep the first row per key — same as the old procs'
    ROW_NUMBER() OVER (PARTITION BY Type, BillNumber, BioguideId ORDER BY ItemElementId) = 1.
    key_len = how many leading columns form the key."""
    seen = set()
    out = []
    for row in rows:
        key = row[:key_len]
        if key in seen or row[key_len - 1] is None:
            continue
        seen.add(key)
        out.append(row)
    return out


# ============================================================
# COLLECTOR — called once per XML file during the Bronze load
# ============================================================

class SilverCollector:
    """Holds parsed rows per bill. If the same bill shows up in more than
    one file, keep the newest one (UpdateDate DESC, FileId DESC), matching
    Silver.BuildBills."""

    def __init__(self):
        self.bills = {}  # (Type, BillNumber) -> dict

    def add(self, root, file_id):
        root = strip_namespaces(root)
        bill = root.find("bill")
        if bill is None:
            return
        bill_type = trunc(get(bill, "type"), 20)
        bill_number = safe_int(get(bill, "number"))
        if bill_type is None or bill_number is None:
            return

        key = (bill_type, bill_number)
        rank = (safe_date(get(bill, "updateDate")) or datetime.date.min, file_id)
        existing = self.bills.get(key)
        if existing is not None and existing["rank"] >= rank:
            return

        self.bills[key] = {
            "rank": rank,
            "sponsors": parse_sponsors(bill, bill_type, bill_number, file_id),
            "cosponsors": parse_cosponsors(bill, bill_type, bill_number, file_id),
            "actions": parse_actions(bill, bill_type, bill_number, file_id),
            "subjects": parse_subjects(bill, bill_type, bill_number, file_id),
        }

    def rows(self, table):
        out = []
        for parsed in self.bills.values():
            out.extend(parsed[table])
        return out


# ============================================================
# SQL
# ============================================================

CREATE_SILVER_SQL = """
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'Silver')
    EXEC('CREATE SCHEMA Silver');

IF OBJECT_ID('Silver.Sponsors', 'U') IS NULL
BEGIN
    CREATE TABLE Silver.Sponsors
    (
        Type        VARCHAR(20)  NULL,
        BillNumber  INT          NULL,
        BioguideId  VARCHAR(20)  NULL,
        FullName    VARCHAR(300) NULL,
        FirstName   VARCHAR(100) NULL,
        MiddleName  VARCHAR(100) NULL,
        LastName    VARCHAR(100) NULL,
        Party       VARCHAR(10)  NULL,
        State       VARCHAR(2)   NULL,
        District    INT          NULL,
        IsByRequest VARCHAR(50)  NULL,
        FileId      INT          NOT NULL
    );
    CREATE UNIQUE CLUSTERED INDEX IX_Silver_Sponsors_BillSponsor ON Silver.Sponsors(Type, BillNumber, BioguideId);
    CREATE INDEX IX_Silver_Sponsors_BioguideId ON Silver.Sponsors(BioguideId);
    CREATE INDEX IX_Silver_Sponsors_FileId ON Silver.Sponsors(FileId);
END

IF OBJECT_ID('Silver.Cosponsors', 'U') IS NULL
BEGIN
    CREATE TABLE Silver.Cosponsors
    (
        Type                VARCHAR(20)  NULL,
        BillNumber          INT          NULL,
        BioguideId          VARCHAR(20)  NULL,
        FullName            VARCHAR(300) NULL,
        FirstName           VARCHAR(100) NULL,
        MiddleName          VARCHAR(100) NULL,
        LastName            VARCHAR(100) NULL,
        Party               VARCHAR(10)  NULL,
        State               VARCHAR(2)   NULL,
        District            INT          NULL,
        SponsorshipDate     DATE         NULL,
        IsOriginalCosponsor VARCHAR(5)   NULL,
        FileId              INT          NOT NULL
    );
    CREATE UNIQUE CLUSTERED INDEX IX_Silver_Cosponsors_BillCosponsor ON Silver.Cosponsors(Type, BillNumber, BioguideId);
    CREATE INDEX IX_Silver_Cosponsors_BioguideId ON Silver.Cosponsors(BioguideId);
    CREATE INDEX IX_Silver_Cosponsors_FileId ON Silver.Cosponsors(FileId);
END

IF OBJECT_ID('Silver.Actions', 'U') IS NULL
BEGIN
    CREATE TABLE Silver.Actions
    (
        Type             VARCHAR(20)    NOT NULL,
        BillNumber       INT            NOT NULL,
        ActionSeq        INT            NOT NULL,
        ActionDate       DATE           NULL,
        ActionTime       VARCHAR(20)    NULL,
        ActionCode       VARCHAR(50)    NULL,
        ActionType       VARCHAR(100)   NULL,
        ActionText       NVARCHAR(MAX)  NULL,
        SourceSystemName VARCHAR(200)   NULL,
        SourceSystemCode VARCHAR(20)    NULL,
        RollNumber       INT            NULL,
        VoteChamber      VARCHAR(50)    NULL,
        VoteDate         DATE           NULL,
        VoteUrl          VARCHAR(500)   NULL,
        FileId           INT            NOT NULL
    );
    CREATE UNIQUE CLUSTERED INDEX IX_Silver_Actions_BillSeq ON Silver.Actions(Type, BillNumber, ActionSeq);
END

IF OBJECT_ID('Silver.Subjects', 'U') IS NULL
BEGIN
    CREATE TABLE Silver.Subjects
    (
        Type        VARCHAR(20)  NOT NULL,
        BillNumber  INT          NOT NULL,
        SubjectType VARCHAR(30)  NOT NULL,
        SubjectName VARCHAR(300) NOT NULL,
        FileId      INT          NOT NULL
    );
    CREATE UNIQUE CLUSTERED INDEX IX_Silver_Subjects_BillSubject ON Silver.Subjects(Type, BillNumber, SubjectType, SubjectName);
    CREATE INDEX IX_Silver_Subjects_SubjectName ON Silver.Subjects(SubjectName);
END
"""

INSERTS = {
    "sponsors": (
        "Silver.Sponsors",
        "INSERT INTO Silver.Sponsors (Type, BillNumber, BioguideId, FullName, FirstName, MiddleName, "
        "LastName, Party, State, District, IsByRequest, FileId) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        3,  # dedupe key: Type, BillNumber, BioguideId
    ),
    "cosponsors": (
        "Silver.Cosponsors",
        "INSERT INTO Silver.Cosponsors (Type, BillNumber, BioguideId, FullName, FirstName, MiddleName, "
        "LastName, Party, State, District, SponsorshipDate, IsOriginalCosponsor, FileId) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        3,
    ),
    "actions": (
        "Silver.Actions",
        "INSERT INTO Silver.Actions (Type, BillNumber, ActionSeq, ActionDate, ActionTime, ActionCode, "
        "ActionType, ActionText, SourceSystemName, SourceSystemCode, RollNumber, VoteChamber, VoteDate, "
        "VoteUrl, FileId) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        3,
    ),
    "subjects": (
        "Silver.Subjects",
        "INSERT INTO Silver.Subjects (Type, BillNumber, SubjectType, SubjectName, FileId) VALUES (?,?,?,?,?)",
        4,
    ),
}


def write_silver(connection, collector):
    """Truncate + reload every Silver table in ONE transaction, so if
    anything fails the web app keeps seeing yesterday's data."""
    cursor = connection.cursor()
    try:
        cursor.execute(CREATE_SILVER_SQL)
        connection.commit()

        for name, (table, insert_sql, key_len) in INSERTS.items():
            rows = dedupe(collector.rows(name), key_len)
            cursor.execute(f"TRUNCATE TABLE {table}")
            cursor.fast_executemany = True
            for start in range(0, len(rows), CHUNK_SIZE):
                cursor.executemany(insert_sql, rows[start:start + CHUNK_SIZE])
            logging.info("%s loaded: %s rows", table, len(rows))

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
