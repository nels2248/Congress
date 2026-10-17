
CREATE   PROCEDURE [Silver].[BuildSponsors]
AS
BEGIN
    SET NOCOUNT ON;

    ------------------------------------------------------------
    -- 1. Drop existing table
    ------------------------------------------------------------
    IF OBJECT_ID('Silver.Sponsors', 'U') IS NOT NULL
        DROP TABLE Silver.Sponsors;


    ------------------------------------------------------------
    -- 2. Materialize only the sponsor ITEM elements we need
    ------------------------------------------------------------
    IF OBJECT_ID('tempdb..#SponsorItems') IS NOT NULL
        DROP TABLE #SponsorItems;

    SELECT
        e.ElementId AS ItemElementId,
        e.FileId
    INTO #SponsorItems
    FROM Bronze.XmlElement e
    INNER JOIN Silver.Bills b
        ON b.FileId = e.FileId
    WHERE e.XmlPath = 'billStatus/bill/sponsors/item';


    CREATE UNIQUE CLUSTERED INDEX IX_SponsorItems
        ON #SponsorItems(ItemElementId);


    CREATE INDEX IX_SponsorItems_FileId
        ON #SponsorItems(FileId);


    ------------------------------------------------------------
    -- 3. Pull ONLY child elements belonging to those sponsors
    ------------------------------------------------------------
    IF OBJECT_ID('tempdb..#SponsorFields') IS NOT NULL
        DROP TABLE #SponsorFields;

    SELECT
        si.ItemElementId,
        si.FileId,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/sponsors/item/bioguideId'
            THEN v.Value
        END) AS VARCHAR(20)) AS BioguideId,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/sponsors/item/fullName'
            THEN v.Value
        END) AS VARCHAR(300)) AS FullName,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/sponsors/item/firstName'
            THEN v.Value
        END) AS VARCHAR(100)) AS FirstName,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/sponsors/item/middleName'
            THEN v.Value
        END) AS VARCHAR(100)) AS MiddleName,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/sponsors/item/lastName'
            THEN v.Value
        END) AS VARCHAR(100)) AS LastName,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/sponsors/item/party'
            THEN v.Value
        END) AS VARCHAR(10)) AS Party,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/sponsors/item/state'
            THEN v.Value
        END) AS VARCHAR(2)) AS State,

        TRY_CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/sponsors/item/district'
            THEN v.Value
        END) AS INT) AS District,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/sponsors/item/isByRequest'
            THEN v.Value
        END) AS VARCHAR(50)) AS IsByRequest

    INTO #SponsorFields

    FROM #SponsorItems si

    INNER JOIN Bronze.XmlElement e
        ON e.ParentElementId = si.ItemElementId

    INNER JOIN Bronze.XmlValue v
        ON v.ElementId = e.ElementId

    WHERE v.XmlPath IN
    (
        'billStatus/bill/sponsors/item/bioguideId',
        'billStatus/bill/sponsors/item/fullName',
        'billStatus/bill/sponsors/item/firstName',
        'billStatus/bill/sponsors/item/middleName',
        'billStatus/bill/sponsors/item/lastName',
        'billStatus/bill/sponsors/item/party',
        'billStatus/bill/sponsors/item/state',
        'billStatus/bill/sponsors/item/district',
        'billStatus/bill/sponsors/item/isByRequest'
    )

    GROUP BY
        si.ItemElementId,
        si.FileId;


    CREATE UNIQUE CLUSTERED INDEX IX_SponsorFields
        ON #SponsorFields(ItemElementId);


    CREATE INDEX IX_SponsorFields_FileId
        ON #SponsorFields(FileId);


    ------------------------------------------------------------
    -- 4. Build final Sponsors table
    ------------------------------------------------------------
    ;WITH Deduped AS
    (
        SELECT
            b.Type,
            b.BillNumber,

            sf.BioguideId,
            sf.FullName,
            sf.FirstName,
            sf.MiddleName,
            sf.LastName,
            sf.Party,
            sf.State,
            sf.District,
            sf.IsByRequest,
            sf.FileId,

            ROW_NUMBER() OVER
            (
                PARTITION BY
                    b.Type,
                    b.BillNumber,
                    sf.BioguideId
                ORDER BY
                    sf.ItemElementId
            ) AS RowNum

        FROM #SponsorFields sf

        INNER JOIN Silver.Bills b
            ON b.FileId = sf.FileId

        WHERE sf.BioguideId IS NOT NULL
    )

    SELECT
        Type,
        BillNumber,
        BioguideId,
        FullName,
        FirstName,
        MiddleName,
        LastName,
        Party,
        State,
        District,
        IsByRequest,
        FileId
    INTO Silver.Sponsors

    FROM Deduped

    WHERE RowNum = 1;


    ------------------------------------------------------------
    -- 5. Index final table
    ------------------------------------------------------------
    CREATE UNIQUE CLUSTERED INDEX IX_Silver_Sponsors_BillSponsor
        ON Silver.Sponsors(Type, BillNumber, BioguideId);

    CREATE INDEX IX_Silver_Sponsors_BioguideId
        ON Silver.Sponsors(BioguideId);

    CREATE INDEX IX_Silver_Sponsors_FileId
        ON Silver.Sponsors(FileId);

END

GO

