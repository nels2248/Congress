import datetime
import io
import logging
import os
import re
import socket
import zipfile
import xml.etree.ElementTree as ET

import pyodbc
import requests
import azure.functions as func
import time
import concurrent.futures

URLS = {
    "https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hconres/BILLSTATUS-119-hconres.zip",
    "https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hjres/BILLSTATUS-119-hjres.zip",
    "https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119-hr.zip",
    "https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hres/BILLSTATUS-119-hres.zip",
    "https://www.govinfo.gov/bulkdata/BILLSTATUS/119/s/BILLSTATUS-119-s.zip",
    "https://www.govinfo.gov/bulkdata/BILLSTATUS/119/sconres/BILLSTATUS-119-sconres.zip",
    "https://www.govinfo.gov/bulkdata/BILLSTATUS/119/sjres/BILLSTATUS-119-sjres.zip",
    "https://www.govinfo.gov/bulkdata/BILLSTATUS/119/sres/BILLSTATUS-119-sres.zip",
}

VERBOSE = False


class IdCounter:
    """Generates sequential IDs in Python so we can batch-insert elements
    instead of doing one INSERT per element to get back an IDENTITY value."""
    def __init__(self, start=0):
        self.value = start

    def next(self):
        self.value += 1
        return self.value


# ============================================================
# SQL — schema setup
# ============================================================

CREATE_SCHEMA_SQL = """
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'Bronze')
BEGIN
    EXEC('CREATE SCHEMA Bronze');
END
"""

CREATE_FILE_TABLE_SQL = """
IF OBJECT_ID('Bronze.XmlFile', 'U') IS NULL
BEGIN
    CREATE TABLE Bronze.XmlFile
    (
        FileId          INT IDENTITY(1,1) PRIMARY KEY,
        FileName        NVARCHAR(500) NOT NULL,
        FilePath        NVARCHAR(2000) NOT NULL,
        FileSizeBytes   BIGINT NULL,
        LoadedAt        DATETIME2 NOT NULL
            CONSTRAINT DF_XmlFile_LoadedAt DEFAULT SYSUTCDATETIME()
    );
    CREATE INDEX IX_XmlFile_FilePath ON Bronze.XmlFile(FilePath);
END
"""

CREATE_ELEMENT_TABLE_SQL = """
IF OBJECT_ID('Bronze.XmlElement', 'U') IS NULL
BEGIN
    CREATE TABLE Bronze.XmlElement
    (
        ElementId        BIGINT IDENTITY(1,1) PRIMARY KEY,
        FileId           INT NOT NULL,
        ParentElementId  BIGINT NULL,
        XmlPath          NVARCHAR(2000) NOT NULL,
        ElementName      NVARCHAR(500) NOT NULL,
        Occurrence       INT NOT NULL,
        CONSTRAINT FK_XmlElement_File FOREIGN KEY (FileId) REFERENCES Bronze.XmlFile(FileId),
        CONSTRAINT FK_XmlElement_Parent FOREIGN KEY (ParentElementId) REFERENCES Bronze.XmlElement(ElementId)
    );
    CREATE INDEX IX_XmlElement_FileId ON Bronze.XmlElement(FileId);
    CREATE INDEX IX_XmlElement_ParentElementId ON Bronze.XmlElement(ParentElementId);
    CREATE INDEX IX_XmlElement_XmlPath ON Bronze.XmlElement(XmlPath);
END
"""

CREATE_VALUE_TABLE_SQL = """
IF OBJECT_ID('Bronze.XmlValue', 'U') IS NULL
BEGIN
    CREATE TABLE Bronze.XmlValue
    (
        ValueId    BIGINT IDENTITY(1,1) PRIMARY KEY,
        ElementId  BIGINT NOT NULL,
        XmlPath    NVARCHAR(2000) NOT NULL,
        Value      NVARCHAR(MAX) NULL,
        DataType   VARCHAR(50) NULL,
        CONSTRAINT FK_XmlValue_Element FOREIGN KEY (ElementId) REFERENCES Bronze.XmlElement(ElementId)
    );
    CREATE INDEX IX_XmlValue_ElementId ON Bronze.XmlValue(ElementId); 
    CREATE INDEX IX_XmlValue_XmlPath_Covering ON Bronze.XmlValue(XmlPath) INCLUDE (ElementId, Value);
END
"""

# Delete order matters — children before parents, due to foreign keys
TRUNCATE_SQL = [
    "ALTER TABLE Bronze.XmlValue DROP CONSTRAINT FK_XmlValue_Element;",
    "ALTER TABLE Bronze.XmlElement DROP CONSTRAINT FK_XmlElement_File;",
    "TRUNCATE TABLE Bronze.XmlValue;",
    "TRUNCATE TABLE Bronze.XmlElement;",
    "TRUNCATE TABLE Bronze.XmlFile;",
    "ALTER TABLE Bronze.XmlValue WITH CHECK ADD CONSTRAINT FK_XmlValue_Element "
    "FOREIGN KEY (ElementId) REFERENCES Bronze.XmlElement(ElementId);",
    "ALTER TABLE Bronze.XmlElement WITH CHECK ADD CONSTRAINT FK_XmlElement_File "
    "FOREIGN KEY (FileId) REFERENCES Bronze.XmlFile(FileId);",
]


# ============================================================
# HELPERS
# ============================================================
def extract_server_host(connection_string):
    """Pulls the SERVER= value out of an ODBC connection string and strips
    a trailing ,port if present, so we can do a raw TCP check against it.
    Returns (host, port) or (None, None) if it can't be parsed."""
    match = re.search(r"SERVER=([^;]+)", connection_string, re.IGNORECASE)
    if not match:
        return None, None

    raw_server = match.group(1).strip()

    # Handle "tcp:hostname,1433" or "hostname,1433" or just "hostname"
    raw_server = raw_server.replace("tcp:", "")
    if "," in raw_server:
        host, port_str = raw_server.split(",", 1)
        try:
            port = int(port_str)
        except ValueError:
            port = 1433
        return host.strip(), port

    return raw_server, 1433


def check_tcp_reachable(host, port=1433, timeout=10):
    """Raw TCP connectivity check, independent of pyodbc/ODBC driver.
    Used to tell apart a network-layer hang (firewall dropping packets)
    from a slower SQL-level negotiation issue."""
    if not host:
        logging.warning("TCP check skipped — could not parse server host from connection string")
        return None
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed = time.time() - start
            logging.info("TCP check to %s:%s succeeded in %.2fs", host, port, elapsed)
            return True
    except Exception as e:
        elapsed = time.time() - start
        logging.warning("TCP check to %s:%s failed after %.2fs: %s", host, port, elapsed, e)
        return False


def connect_with_retry(connection_string, max_attempts=5, delay_seconds=15):
    """Azure SQL serverless databases auto-pause when idle. The first
    connection after a pause triggers a resume but fails immediately
    with error 40613, or the ODBC driver simply times out waiting
    (HYT00 / 08001 / 08S01) - retry a few times while it wakes up."""
    last_error = None
    RESUME_CODES = ("40613", "HYT00", "08001", "08S01")
    server_host, server_port = extract_server_host(connection_string)

    for attempt in range(1, max_attempts + 1):
        logging.info("Attempting database connection (attempt %s/%s)...", attempt, max_attempts)

        # Raw TCP check first — tells us if this is a network-layer hang
        # (firewall dropping packets) vs. a SQL-level auth/negotiation issue,
        # independent of whatever pyodbc/the ODBC driver does next.
        check_tcp_reachable(server_host, server_port, timeout=15)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(pyodbc.connect, connection_string, timeout=60)
            try:
                return future.result(timeout=75)
            except concurrent.futures.TimeoutError:
                last_error = TimeoutError("pyodbc.connect hung past hard timeout")
                logging.warning(
                    "Connection attempt %s/%s hung past hard timeout, treating as resumable, waiting %ss...",
                    attempt, max_attempts, delay_seconds
                )
                time.sleep(delay_seconds)
            except pyodbc.Error as e:
                last_error = e
                if any(code in str(e) for code in RESUME_CODES):
                    logging.info(
                        "Database is resuming (attempt %s/%s), waiting %ss...",
                        attempt, max_attempts, delay_seconds
                    )
                    time.sleep(delay_seconds)
                else:
                    raise
    raise last_error

def strip_namespace(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def infer_data_type(value):
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return "text"
    if value.lower() in {"true", "false", "yes", "no"}:
        return "boolean"
    try:
        int(value)
        return "integer"
    except ValueError:
        pass
    try:
        float(value)
        return "decimal"
    except ValueError:
        pass
    return "text"


# ============================================================
# DATABASE SETUP
# ============================================================

def setup_database(connection):
    cursor = connection.cursor()
    cursor.execute(CREATE_SCHEMA_SQL)
    cursor.execute(CREATE_FILE_TABLE_SQL)
    cursor.execute(CREATE_ELEMENT_TABLE_SQL)
    cursor.execute(CREATE_VALUE_TABLE_SQL)
    connection.commit()
    cursor.close()


def truncate_bronze(connection):
    """Wipes all three Bronze tables so this run starts completely fresh."""
    logging.info("into truncate bronze")
    cursor = connection.cursor()
    logging.info("past curstor connection in truncate bronze")
    for statement in TRUNCATE_SQL:
        logging.info("into statement for loop")
        logging.info(statement)
        cursor.execute(statement)
        logging.info("statement completed in for loop on statement in bronze")
    logging.info("for loop done in bronze")
    connection.commit()
    logging.info("stuff committed in bronze")

    cursor.close()
    logging.info("Bronze tables cleared — starting fresh load")


def insert_file(connection, entry_name, source_url, size_bytes):
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO Bronze.XmlFile (FileName, FilePath, FileSizeBytes)
        OUTPUT INSERTED.FileId
        VALUES (?, ?, ?)
        """,
        entry_name,
        f"{source_url}!{entry_name}",
        size_bytes,
    )
    file_id = cursor.fetchone()[0]
    cursor.close()
    return file_id


# ============================================================
# XML PROCESSING
# ============================================================

def bulk_insert_elements(cursor, element_rows):
    if not element_rows:
        return

    cursor.execute("SET IDENTITY_INSERT Bronze.XmlElement ON")
    cursor.fast_executemany = True
    cursor.executemany(
        """
        INSERT INTO Bronze.XmlElement (ElementId, FileId, ParentElementId, XmlPath, ElementName, Occurrence)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        element_rows,
    )
    cursor.execute("SET IDENTITY_INSERT Bronze.XmlElement OFF")


def process_element(element, file_id, parent_element_id, parent_path, occurrence_tracker, id_counter, element_rows, value_rows):
    element_name = strip_namespace(element.tag)
    xml_path = f"{parent_path}/{element_name}" if parent_path else element_name

    occurrence_tracker[xml_path] = occurrence_tracker.get(xml_path, 0) + 1
    occurrence = occurrence_tracker[xml_path]

    if VERBOSE:
        logging.info("    %s", xml_path)

    element_id = id_counter.next()
    element_rows.append((element_id, file_id, parent_element_id, xml_path, element_name, occurrence))

    elements_processed = 1
    values_processed = 0

    if element.text and element.text.strip():
        value = element.text.strip()
        data_type = infer_data_type(value)
        value_rows.append((element_id, xml_path, value, data_type))
        values_processed += 1

    for child in element:
        child_elements, child_values = process_element(
            child, file_id, element_id, xml_path, occurrence_tracker, id_counter, element_rows, value_rows
        )
        elements_processed += child_elements
        values_processed += child_values

    return elements_processed, values_processed

def bulk_insert_values(cursor, value_rows):
    if not value_rows:
        return

    cursor.fast_executemany = True

    cursor.executemany(
        """
        INSERT INTO Bronze.XmlValue (ElementId, XmlPath, Value, DataType)
        VALUES (?, ?, ?, ?)
        """,
        value_rows,
    )

def process_xml_bytes(connection, entry_name, source_url, raw_bytes, id_counter):
    try:
        root = ET.fromstring(raw_bytes)
    except ET.ParseError as ex:
        logging.warning("  ERROR parsing %s: %s", entry_name, ex)
        return {"status": "error", "elements": 0, "values": 0}

    file_id = insert_file(connection, entry_name, source_url, len(raw_bytes))

    cursor = connection.cursor()
    occurrence_tracker = {}
    element_rows = []
    value_rows = []
    try:
        elements_processed, values_processed = process_element(
            root, file_id, None, "", occurrence_tracker, id_counter, element_rows, value_rows
        )

        bulk_insert_elements(cursor, element_rows)
        bulk_insert_values(cursor, value_rows)

        connection.commit()
        cursor.close()
        return {"status": "loaded", "elements": elements_processed, "values": values_processed}
    except Exception:
        connection.rollback()
        cursor.close()
        raise


# ============================================================
# FUNCTION ENTRY POINT
# ============================================================

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Starting Congress XML load at %s", utc_timestamp)
    logging.info("Before the connection string")
    connection_string = os.environ["CONGRESS_SQL_CONNECTION_STRING"]
    logging.info("After the connection string")
    connection = connect_with_retry(connection_string)
    logging.info("after connection object created")
    try:
        logging.info("into the try on main")
        setup_database(connection)
        logging.info("past the setup_datbase call")
        truncate_bronze(connection)
        logging.info("truncating bronze")

        loaded = errors = 0
        total_elements = total_values = 0
        id_counter = IdCounter()

        for url in URLS:
            logging.info("Downloading %s", url)
            response = requests.get(url)
            response.raise_for_status()
            logging.info("Downloaded %.1f KB", len(response.content) / 1024)

            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
                file_count = len(xml_names)
                zip_start_time = time.time()
                logging.info("Zip contains %s XML files", file_count)

                for i, entry_name in enumerate(xml_names, 1):
                    logging.info("Starting XML file: %s", entry_name)

                    raw_bytes = zf.read(entry_name)

                    try:                    
                        result = process_xml_bytes(
                            connection,
                            entry_name,
                            url,
                            raw_bytes,
                            id_counter
                        )
                    except Exception as ex:
                        errors += 1
                        logging.error(
                            "ERROR on %s: %s",
                            entry_name,
                            ex,
                            exc_info=True
                        )
                        continue

                    if result["status"] == "loaded":
                        loaded += 1
                        total_elements += result["elements"]
                        total_values += result["values"]

                        logging.info(
                            "Completed XML file: %s — elements=%s values=%s",
                            entry_name,
                            result["elements"],
                            result["values"],
                        )

                    elif result["status"] == "error":
                        errors += 1
                        logging.error(
                            "XML parse error: %s",
                            entry_name
                        )

                    if i % 50 == 0 or i == file_count:
                        elapsed = time.time() - zip_start_time
                        logging.info(
                            "Progress: %s/%s files (%.0f%%) — %.1fs elapsed, %.2f files/sec",
                            i, file_count, i / file_count * 100, elapsed, i / elapsed if elapsed > 0 else 0
                        )

        logging.info(
            "Load complete — loaded=%s errors=%s elements=%s values=%s",
            loaded,
            errors,
            total_elements,
            total_values,
        ) 

        # BUILD SILVER LAYER — only runs if the Bronze load above completed
        # without raising, so Silver never rebuilds from a partial/broken load
        logging.info("Building Silver.Bills from Bronze data...")
        cursor = connection.cursor()
        cursor.execute("EXEC Silver.BuildBills")
        connection.commit()
        cursor.close()
        logging.info("Silver.Bills build complete")
    finally:
        connection.close()