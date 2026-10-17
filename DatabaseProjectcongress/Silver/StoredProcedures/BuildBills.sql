

CREATE     PROCEDURE [Silver].[BuildBills]
AS
BEGIN
    SET NOCOUNT ON;

    IF OBJECT_ID('Silver.Bills', 'U') IS NOT NULL
        DROP TABLE Silver.Bills;

    WITH BillFiles AS
    (
        SELECT
            CAST(MAX(CASE 
                WHEN v.XmlPath = 'billStatus/bill/number'
                THEN v.Value
            END) AS INT) AS BillNumber,

            CAST(MAX(CASE 
                WHEN v.XmlPath = 'billStatus/bill/type'
                THEN v.Value
            END) AS VARCHAR(20)) AS Type,

            TRY_CONVERT(date, MAX(CASE 
                WHEN v.XmlPath = 'billStatus/bill/updateDate'
                THEN v.Value
            END)) AS UpdateDate,

            CAST(MAX(CASE 
                WHEN v.XmlPath = 'billStatus/bill/originChamber'
                THEN v.Value
            END) AS VARCHAR(50)) AS OriginChamber,

            TRY_CONVERT(date, MAX(CASE 
                WHEN v.XmlPath = 'billStatus/bill/introducedDate'
                THEN v.Value
            END)) AS IntroducedDate,

            CAST(MAX(CASE 
                WHEN v.XmlPath = 'billStatus/bill/legislationUrl'
                THEN v.Value
            END) AS VARCHAR(500)) AS LegislationUrl,

            CAST(MAX(CASE 
                WHEN v.XmlPath = 'billStatus/bill/policyArea/name'
                THEN v.Value
            END) AS VARCHAR(200)) AS PolicyArea,

            CAST(MAX(CASE 
                WHEN v.XmlPath = 'billStatus/bill/title'
                THEN v.Value
            END) AS VARCHAR(2000)) AS Title,

            TRY_CONVERT(date, MAX(CASE 
                WHEN v.XmlPath = 'billStatus/bill/latestAction/actionDate'
                THEN v.Value
            END)) AS LatestActionDate,

            CAST(MAX(CASE 
                WHEN v.XmlPath = 'billStatus/bill/latestAction/text'
                THEN v.Value
            END) AS VARCHAR(2000)) AS LatestAction,

            e.FileId

        FROM Bronze.XmlValue v
        INNER JOIN Bronze.XmlElement e
            ON v.ElementId = e.ElementId

        WHERE v.XmlPath IN
        (
            'billStatus/bill/number',
            'billStatus/bill/type',
            'billStatus/bill/updateDate',
            'billStatus/bill/originChamber',
            'billStatus/bill/introducedDate',
            'billStatus/bill/legislationUrl',
            'billStatus/bill/policyArea/name',
            'billStatus/bill/title',
            'billStatus/bill/latestAction/actionDate',
            'billStatus/bill/latestAction/text'
        )

        GROUP BY e.FileId
    ),

    RankedBills AS
    (
        SELECT
            *,
            ROW_NUMBER() OVER
            (
                PARTITION BY Type, BillNumber
                ORDER BY UpdateDate DESC, FileId DESC
            ) AS RowNum
        FROM BillFiles
        WHERE Type IS NOT NULL
          AND BillNumber IS NOT NULL
    )

    SELECT
        BillNumber,
        Type,
        UpdateDate,
        OriginChamber,
        IntroducedDate,
        LegislationUrl,
        PolicyArea,
        Title,
        LatestActionDate,
        LatestAction,
        FileId
    INTO Silver.Bills
    FROM RankedBills
    WHERE RowNum = 1;

    CREATE UNIQUE CLUSTERED INDEX IX_Silver_Bills_BillId
        ON Silver.Bills(Type, BillNumber);

    CREATE INDEX IX_Silver_Bills_BillNumber
        ON Silver.Bills(BillNumber);

    CREATE INDEX IX_Silver_Bills_FileId
        ON Silver.Bills(FileId);

END

GO

