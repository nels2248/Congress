"""
BuildNetworkGraph — Timer Trigger function.

Runs the Silver.Sponsors and Silver.Cosponsors build procedures first,
then reads those tables, projects them into a person-to-person
cosponsorship network (sponsor <-> each cosponsor, per bill),
runs Louvain community detection, and writes the result to
Gold.NetworkNodes / Gold.NetworkEdges for Congress.Web.

requirements.txt additions needed:
networkx>=3.0
pandas
pyodbc

(python-louvain is NOT needed separately —
louvain_communities ships inside networkx.algorithms.community
as of networkx 3.0)
"""

import datetime
import logging
import os

import networkx as nx
import pandas as pd
import pyodbc
import azure.functions as func

from networkx.algorithms.community import louvain_communities


# ============================================================
# SQL — schema / table setup
# ============================================================

CREATE_SCHEMA_SQL = """
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'Gold')
BEGIN
    EXEC('CREATE SCHEMA Gold');
END
"""

CREATE_NODES_TABLE_SQL = """
IF OBJECT_ID('Gold.NetworkNodes', 'U') IS NOT NULL
    DROP TABLE Gold.NetworkNodes;

CREATE TABLE Gold.NetworkNodes
(
    BioguideId   VARCHAR(20)  NOT NULL PRIMARY KEY,
    FullName     VARCHAR(300) NULL,
    Party        VARCHAR(10)  NULL,
    State        VARCHAR(2)   NULL,
    CommunityId  INT          NOT NULL,
    BillCount    INT          NOT NULL
);
"""

CREATE_EDGES_TABLE_SQL = """
IF OBJECT_ID('Gold.NetworkEdges', 'U') IS NOT NULL
    DROP TABLE Gold.NetworkEdges;

CREATE TABLE Gold.NetworkEdges
(
    Person1BioguideId VARCHAR(20) NOT NULL,
    Person2BioguideId VARCHAR(20) NOT NULL,
    SharedBillCount   INT         NOT NULL,
    IsCrossParty      BIT         NOT NULL
);

CREATE INDEX IX_Gold_NetworkEdges_Person1
    ON Gold.NetworkEdges(Person1BioguideId);

CREATE INDEX IX_Gold_NetworkEdges_Person2
    ON Gold.NetworkEdges(Person2BioguideId);
"""


# ============================================================
# CONNECTION HELPER
# ============================================================

def connect_with_retry(connection_string, max_attempts=5, delay_seconds=15):
    import time

    last_error = None
    RESUME_CODES = ("40613", "HYT00", "08001", "08S01")

    for attempt in range(1, max_attempts + 1):
        try:
            return pyodbc.connect(connection_string, timeout=60)

        except pyodbc.Error as e:
            last_error = e

            if any(code in str(e) for code in RESUME_CODES):
                logging.info(
                    "Database resuming (attempt %s/%s), waiting %ss...",
                    attempt,
                    max_attempts,
                    delay_seconds
                )
                time.sleep(delay_seconds)
            else:
                raise

    raise last_error


# ============================================================
# BUILD SILVER TABLES
# ============================================================

def build_silver_tables(connection):
    """
    Rebuild Silver.Sponsors and Silver.Cosponsors before
    building the network graph.
    """

    cursor = connection.cursor()

    try:
        logging.info("Starting Silver.BuildSponsors...")
        cursor.execute("EXEC Silver.BuildSponsors")
        connection.commit()
        logging.info("Silver.BuildSponsors completed successfully.")

        logging.info("Starting Silver.BuildCosponsors...")
        cursor.execute("EXEC Silver.BuildCosponsors")
        connection.commit()
        logging.info("Silver.BuildCosponsors completed successfully.")

    finally:
        cursor.close()


# ============================================================
# GRAPH BUILD
# ============================================================

def build_network(sponsors_df: pd.DataFrame, cosponsors_df: pd.DataFrame):
    """
    Returns (nodes_df, edges_df).

    Edge model: for each bill, connect the sponsor to each cosponsor
    (a star per bill), NOT every cosponsor-pair — a bill with 200
    cosponsors would otherwise create ~20,000 near-meaningless edges.

    Weight = number of distinct bills a pair shares this way.
    """

    # One row per person we've ever seen, first non-null
    # Party/State/FullName wins.
    person_info = (
        pd.concat([
            sponsors_df[
                ["BioguideId", "FullName", "Party", "State"]
            ],
            cosponsors_df[
                ["BioguideId", "FullName", "Party", "State"]
            ],
        ])
        .dropna(subset=["BioguideId"])
        .drop_duplicates(
            subset=["BioguideId"],
            keep="first"
        )
        .set_index("BioguideId")
    )

    # Sponsor <-> cosponsor pairs,
    # one row per (bill, sponsor, cosponsor)
    merged = sponsors_df[
        ["Type", "BillNumber", "BioguideId"]
    ].merge(
        cosponsors_df[
            ["Type", "BillNumber", "BioguideId"]
        ],
        on=["Type", "BillNumber"],
        suffixes=("_sponsor", "_cosponsor"),
    )

    # Normalize each pair into an order-independent edge key
    # so (A,B) and (B,A) aggregate together.
    def make_edge_key(row):
        a = row["BioguideId_sponsor"]
        b = row["BioguideId_cosponsor"]

        return (a, b) if a < b else (b, a)

    merged["EdgeKey"] = merged.apply(make_edge_key, axis=1)

    merged = merged.drop_duplicates(
        subset=["Type", "BillNumber", "EdgeKey"]
    )

    edge_counts = (
        merged.groupby("EdgeKey")
        .size()
        .reset_index(name="SharedBillCount")
    )

    edge_counts["Person1BioguideId"] = (
        edge_counts["EdgeKey"]
        .apply(lambda k: k[0])
    )

    edge_counts["Person2BioguideId"] = (
        edge_counts["EdgeKey"]
        .apply(lambda k: k[1])
    )

    def is_cross_party(row):
        p1 = person_info["Party"].get(
            row["Person1BioguideId"]
        )

        p2 = person_info["Party"].get(
            row["Person2BioguideId"]
        )

        if p1 is None or p2 is None:
            return False

        return p1 != p2

    edge_counts["IsCrossParty"] = (
        edge_counts.apply(is_cross_party, axis=1)
    )

    edges_df = edge_counts[
        [
            "Person1BioguideId",
            "Person2BioguideId",
            "SharedBillCount",
            "IsCrossParty",
        ]
    ]

    # Build graph for community detection
    G = nx.Graph()

    for _, row in edges_df.iterrows():
        G.add_edge(
            row["Person1BioguideId"],
            row["Person2BioguideId"],
            weight=row["SharedBillCount"],
        )

    communities = louvain_communities(
        G,
        weight="weight",
        seed=42
    )

    community_of = {}

    for community_id, members in enumerate(communities):
        for bioguide_id in members:
            community_of[bioguide_id] = community_id

    bill_count = dict(
        pd.concat([
            sponsors_df.groupby("BioguideId").size(),
            cosponsors_df.groupby("BioguideId").size(),
        ])
        .groupby(level=0)
        .sum()
    )

    nodes_rows = []

    for bioguide_id in G.nodes():

        info = (
            person_info.loc[bioguide_id]
            if bioguide_id in person_info.index
            else None
        )

        nodes_rows.append({
            "BioguideId": bioguide_id,
            "FullName": (
                info["FullName"]
                if info is not None
                else None
            ),
            "Party": (
                info["Party"]
                if info is not None
                else None
            ),
            "State": (
                info["State"]
                if info is not None
                else None
            ),
            "CommunityId": community_of.get(
                bioguide_id,
                -1
            ),
            "BillCount": int(
                bill_count.get(
                    bioguide_id,
                    0
                )
            ),
        })

    nodes_df = pd.DataFrame(nodes_rows)

    return nodes_df, edges_df


# ============================================================
# WRITE TO SQL
# ============================================================

def write_results(
    connection,
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame
):

    cursor = connection.cursor()

    cursor.execute(CREATE_SCHEMA_SQL)
    cursor.execute(CREATE_NODES_TABLE_SQL)
    cursor.execute(CREATE_EDGES_TABLE_SQL)

    connection.commit()

    cursor.fast_executemany = True

    node_rows = list(
        nodes_df.itertuples(
            index=False,
            name=None
        )
    )

    cursor.executemany(
        """
        INSERT INTO Gold.NetworkNodes
            (
                BioguideId,
                FullName,
                Party,
                State,
                CommunityId,
                BillCount
            )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        node_rows,
    )

    edge_rows = [
        (
            r.Person1BioguideId,
            r.Person2BioguideId,
            int(r.SharedBillCount),
            bool(r.IsCrossParty)
        )
        for r in edges_df.itertuples(index=False)
    ]

    cursor.executemany(
        """
        INSERT INTO Gold.NetworkEdges
            (
                Person1BioguideId,
                Person2BioguideId,
                SharedBillCount,
                IsCrossParty
            )
        VALUES (?, ?, ?, ?)
        """,
        edge_rows,
    )

    connection.commit()
    cursor.close()


# ============================================================
# ENTRY POINT
# ============================================================

def main(mytimer: func.TimerRequest) -> None:

    utc_timestamp = (
        datetime.datetime.utcnow()
        .replace(tzinfo=datetime.timezone.utc)
        .isoformat()
    )

    logging.info(
        "Starting network graph build at %s",
        utc_timestamp
    )

    connection_string = os.environ[
        "CONGRESS_SQL_CONNECTION_STRING"
    ]

    connection = connect_with_retry(
        connection_string
    )

    try:

        # ----------------------------------------------------
        # STEP 1 — Rebuild Silver tables
        # ----------------------------------------------------

        logging.info(
            "Refreshing Silver.Sponsors and Silver.Cosponsors..."
        )

        build_silver_tables(connection)

        # ----------------------------------------------------
        # STEP 2 — Read refreshed Silver data
        # ----------------------------------------------------

        logging.info(
            "Loading refreshed Silver.Sponsors..."
        )

        sponsors_df = pd.read_sql(
            """
            SELECT
                Type,
                BillNumber,
                BioguideId,
                FullName,
                Party,
                State
            FROM Silver.Sponsors
            """,
            connection,
        )

        logging.info(
            "Loading refreshed Silver.Cosponsors..."
        )

        cosponsors_df = pd.read_sql(
            """
            SELECT
                Type,
                BillNumber,
                BioguideId,
                FullName,
                Party,
                State
            FROM Silver.Cosponsors
            """,
            connection,
        )

        logging.info(
            "Loaded %s sponsor rows, %s cosponsor rows",
            len(sponsors_df),
            len(cosponsors_df),
        )

        # ----------------------------------------------------
        # STEP 3 — Build graph
        # ----------------------------------------------------

        nodes_df, edges_df = build_network(
            sponsors_df,
            cosponsors_df
        )

        logging.info(
            "Built graph: %s nodes, %s edges, %s communities",
            len(nodes_df),
            len(edges_df),
            nodes_df["CommunityId"].nunique(),
        )

        # ----------------------------------------------------
        # STEP 4 — Write Gold tables
        # ----------------------------------------------------

        write_results(
            connection,
            nodes_df,
            edges_df
        )

        logging.info(
            "Network graph build complete"
        )

    finally:
        connection.close()