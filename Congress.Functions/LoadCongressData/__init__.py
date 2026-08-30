import datetime
import io
import logging
import os
import zipfile
import xml.etree.ElementTree as ET

import pyodbc
import requests
import azure.functions as func
import time

URL = "https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hconres/BILLSTATUS-119-hconres.zip"

VERBOSE = False


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
    CREATE INDEX IX_XmlValue_XmlPath ON Bronze.XmlValue(XmlPath);
END
"""

# Delete order matters — children before parents, due to foreign keys
TRUNCATE_SQL = [
    "DELETE FROM Bronze.XmlValue;",
    "DELETE FROM Bronze.XmlElement;",
    "DELETE FROM Bronze.XmlFile;",
    "DBCC CHECKIDENT ('Bronze.XmlValue', RESEED, 0);",
    "DBCC CHECKIDENT ('Bronze.XmlElement', RESEED, 0);",
    "DBCC CHECKIDENT ('Bronze.XmlFile', RESEED, 0);",
]


# ============================================================
# HELPERS
# ============================================================
def connect_with_retry(connection_string, max_attempts=5, delay_seconds=15):
    """Azure SQL serverless databases auto-pause when idle. The first
    connection after a pause triggers a resume but fails immediately
    with error 40613 - retry a few times while it wakes up."""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return pyodbc.connect(connection_string)
        except pyodbc.Error as e:
            last_error = e
            if "40613" in str(e):
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
    cursor = connection.cursor()
    for statement in TRUNCATE_SQL:
        cursor.execute(statement)
    connection.commit()
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

def insert_element(cursor, file_id, parent_element_id, xml_path, element_name, occurrence):
    cursor.execute(
        """
        INSERT INTO Bronze.XmlElement (FileId, ParentElementId, XmlPath, ElementName, Occurrence)
        OUTPUT INSERTED.ElementId
        VALUES (?, ?, ?, ?, ?)
        """,
        file_id, parent_element_id, xml_path, element_name, occurrence,
    )
    return cursor.fetchone()[0]


def insert_value(cursor, element_id, xml_path, value):
    if value is None:
        return
    value = value.strip()
    if value == "":
        return
    data_type = infer_data_type(value)
    cursor.execute(
        "INSERT INTO Bronze.XmlValue (ElementId, XmlPath, Value, DataType) VALUES (?, ?, ?, ?)",
        element_id, xml_path, value, data_type,
    )


def process_element(cursor, element, file_id, parent_element_id, parent_path, occurrence_tracker):
    element_name = strip_namespace(element.tag)
    xml_path = f"{parent_path}/{element_name}" if parent_path else element_name

    occurrence_tracker[xml_path] = occurrence_tracker.get(xml_path, 0) + 1
    occurrence = occurrence_tracker[xml_path]

    if VERBOSE:
        logging.info("    %s", xml_path)

    element_id = insert_element(cursor, file_id, parent_element_id, xml_path, element_name, occurrence)

    elements_processed = 1
    values_processed = 0

    if element.text and element.text.strip():
        insert_value(cursor, element_id, xml_path, element.text)
        values_processed += 1

    for child in element:
        child_elements, child_values = process_element(
            cursor, child, file_id, element_id, xml_path, occurrence_tracker
        )
        elements_processed += child_elements
        values_processed += child_values

    return elements_processed, values_processed


def process_xml_bytes(connection, entry_name, source_url, raw_bytes):
    try:
        root = ET.fromstring(raw_bytes)
    except ET.ParseError as ex:
        logging.warning("  ERROR parsing %s: %s", entry_name, ex)
        return {"status": "error", "elements": 0, "values": 0}

    file_id = insert_file(connection, entry_name, source_url, len(raw_bytes))

    cursor = connection.cursor()
    occurrence_tracker = {}
    try:
        elements_processed, values_processed = process_element(
            cursor, root, file_id, None, "", occurrence_tracker
        )
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

    response = requests.get(URL)
    response.raise_for_status()
    logging.info("Downloaded %.1f KB", len(response.content) / 1024)

    connection_string = os.environ["CONGRESS_SQL_CONNECTION_STRING"]
    connection = connect_with_retry(connection_string)

    try:
        setup_database(connection)
        truncate_bronze(connection)

        loaded = errors = 0
        total_elements = total_values = 0

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
            logging.info("Zip contains %s XML files", len(xml_names))

            for entry_name in xml_names:
                raw_bytes = zf.read(entry_name)

                try:
                    result = process_xml_bytes(connection, entry_name, URL, raw_bytes)
                except Exception as ex:
                    errors += 1
                    logging.error("  ERROR on %s: %s", entry_name, ex)
                    continue

                if result["status"] == "loaded":
                    loaded += 1
                    total_elements += result["elements"]
                    total_values += result["values"]
                elif result["status"] == "error":
                    errors += 1

        logging.info(
            "Load complete — loaded=%s errors=%s elements=%s values=%s",
            loaded, errors, total_elements, total_values,
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