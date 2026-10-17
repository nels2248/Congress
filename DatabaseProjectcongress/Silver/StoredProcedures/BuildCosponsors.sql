
CREATE     PROCEDURE [Silver].[BuildCosponsors]
AS
BEGIN
    SET NOCOUNT ON;

    IF OBJECT_ID('Silver.Cosponsors', 'U') IS NOT NULL
        DROP TABLE Silver.Cosponsors;

    ------------------------------------------------------------
    -- Step 1: Materialize cosponsor items
    ------------------------------------------------------------
    DROP TABLE IF EXISTS #CosponsorItems;

    SELECT
        e.ElementId AS ItemElementId,
        e.FileId
    INTO #CosponsorItems
    FROM Bronze.XmlElement e
    WHERE e.XmlPath = 'billStatus/bill/cosponsors/item';

    CREATE UNIQUE CLUSTERED INDEX IX_CosponsorItems
        ON #CosponsorItems(ItemElementId);

    CREATE INDEX IX_CosponsorItems_FileId
        ON #CosponsorItems(FileId);


    ------------------------------------------------------------
    -- Step 2: Build cosponsor fields
    ------------------------------------------------------------
    DROP TABLE IF EXISTS #CosponsorFields;

    SELECT
        ci.ItemElementId,
        ci.FileId,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/cosponsors/item/bioguideId'
            THEN v.Value
        END) AS VARCHAR(20)) AS BioguideId,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/cosponsors/item/fullName'
            THEN v.Value
        END) AS VARCHAR(300)) AS FullName,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/cosponsors/item/firstName'
            THEN v.Value
        END) AS VARCHAR(100)) AS FirstName,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/cosponsors/item/middleName'
            THEN v.Value
        END) AS VARCHAR(100)) AS MiddleName,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/cosponsors/item/lastName'
            THEN v.Value
        END) AS VARCHAR(100)) AS LastName,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/cosponsors/item/party'
            THEN v.Value
        END) AS VARCHAR(10)) AS Party,

        CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/cosponsors/item/state'
            THEN v.Value
        END) AS VARCHAR(2)) AS State,

        TRY_CAST(MAX(CASE
            WHEN v.XmlPath = 'billStatus/bill/cosponsors/item/district'
            THEN v.Value
        END) AS INT) AS District,

        TRY_CONVERT(
            date,
            MAX(CASE
                WHEN v.XmlPath =
                    'billStatus/bill/cosponsors/item/sponsorshipDate'
                THEN v.Value
            END)
        ) AS SponsorshipDate,

        CAST(MAX(CASE
            WHEN v.XmlPath =
                'billStatus/bill/cosponsors/item/isOriginalCosponsor'
            THEN v.Value
        END) AS VARCHAR(5)) AS IsOriginalCosponsor

    INTO #CosponsorFields
    FROM #CosponsorItems ci
    INNER JOIN Bronze.XmlElement e
        ON e.ParentElementId = ci.ItemElementId
    INNER JOIN Bronze.XmlValue v WITH (INDEX(IX_XmlValue_ElementId_XmlPath))
        ON v.ElementId = e.ElementId
    WHERE v.XmlPath IN
    (
        'billStatus/bill/cosponsors/item/bioguideId',
        'billStatus/bill/cosponsors/item/fullName',
        'billStatus/bill/cosponsors/item/firstName',
        'billStatus/bill/cosponsors/item/middleName',
        'billStatus/bill/cosponsors/item/lastName',
        'billStatus/bill/cosponsors/item/party',
        'billStatus/bill/cosponsors/item/state',
        'billStatus/bill/cosponsors/item/district',
        'billStatus/bill/cosponsors/item/sponsorshipDate',
        'billStatus/bill/cosponsors/item/isOriginalCosponsor'
    )
    GROUP BY
        ci.ItemElementId,
        ci.FileId
    OPTION (RECOMPILE);


    CREATE UNIQUE CLUSTERED INDEX IX_CosponsorFields
        ON #CosponsorFields(ItemElementId);

    CREATE INDEX IX_CosponsorFields_FileId
        ON #CosponsorFields(FileId);


    ------------------------------------------------------------
    -- Step 3: Deduplicate
    ------------------------------------------------------------
    ;WITH Deduped AS
    (
        SELECT
            b.Type,
            b.BillNumber,
            cf.BioguideId,
            cf.FullName,
            cf.FirstName,
            cf.MiddleName,
            cf.LastName,
            cf.Party,
            cf.State,
            cf.District,
            cf.SponsorshipDate,
            cf.IsOriginalCosponsor,
            cf.FileId,
            ROW_NUMBER() OVER
            (
                PARTITION BY
                    b.Type,
                    b.BillNumber,
                    cf.BioguideId
                ORDER BY
                    cf.ItemElementId
            ) AS RowNum
        FROM #CosponsorFields cf
        INNER JOIN Silver.Bills b
            ON b.FileId = cf.FileId
        WHERE cf.BioguideId IS NOT NULL
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
        SponsorshipDate,
        IsOriginalCosponsor,
        FileId
    INTO Silver.Cosponsors
    FROM Deduped
    WHERE RowNum = 1;


    ------------------------------------------------------------
    -- Step 4: Index final table
    ------------------------------------------------------------
    CREATE UNIQUE CLUSTERED INDEX IX_Silver_Cosponsors_BillCosponsor
        ON Silver.Cosponsors(Type, BillNumber, BioguideId);

    CREATE INDEX IX_Silver_Cosponsors_BioguideId
        ON Silver.Cosponsors(BioguideId);

    CREATE INDEX IX_Silver_Cosponsors_FileId
        ON Silver.Cosponsors(FileId);

END

GO

