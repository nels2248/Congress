CREATE OR ALTER PROCEDURE Silver.BuildBills
AS
BEGIN
    SET NOCOUNT ON;

    IF OBJECT_ID('Silver.Bills', 'U') IS NOT NULL
        DROP TABLE Silver.Bills;

    SELECT
        CAST(MAX(CASE WHEN v.XmlPath = 'billStatus/bill/number' THEN v.Value END) AS INT) AS BillNumber,
        TRY_CONVERT(date, MAX(CASE WHEN v.XmlPath = 'billStatus/bill/updateDate' THEN v.Value END)) AS UpdateDate,
        MAX(CASE WHEN v.XmlPath = 'billStatus/bill/originChamber' THEN v.Value END) AS OriginChamber,
        TRY_CONVERT(date, MAX(CASE WHEN v.XmlPath = 'billStatus/bill/introducedDate' THEN v.Value END)) AS IntroducedDate,
        MAX(CASE WHEN v.XmlPath = 'billStatus/bill/legislationUrl' THEN v.Value END) AS LegislationUrl,
        MAX(CASE WHEN v.XmlPath = 'billStatus/bill/policyArea/name' THEN v.Value END) AS PolicyArea,
        MAX(CASE WHEN v.XmlPath = 'billStatus/bill/title' THEN v.Value END) AS Title,
        TRY_CONVERT(date, MAX(CASE WHEN v.XmlPath = 'billStatus/bill/latestAction/actionDate' THEN v.Value END)) AS LatestActionDate,
        MAX(CASE WHEN v.XmlPath = 'billStatus/bill/latestAction/text' THEN v.Value END) AS LatestAction,
        f.FileId
    INTO Silver.Bills
    FROM Bronze.XmlValue v
    INNER JOIN Bronze.XmlElement e ON v.ElementId = e.ElementId
    INNER JOIN Bronze.XmlFile f ON e.FileId = f.FileId
    GROUP BY f.FileId;

    CREATE UNIQUE CLUSTERED INDEX IX_Silver_Bills_FileId ON Silver.Bills(FileId);
    CREATE INDEX IX_Silver_Bills_BillNumber ON Silver.Bills(BillNumber);
END