CREATE TABLE [Silver].[Cosponsors] (
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


GO

CREATE UNIQUE CLUSTERED INDEX IX_Silver_Cosponsors_BillCosponsor ON Silver.Cosponsors(Type, BillNumber, BioguideId);


GO

CREATE INDEX IX_Silver_Cosponsors_BioguideId ON Silver.Cosponsors(BioguideId);


GO

CREATE INDEX IX_Silver_Cosponsors_FileId ON Silver.Cosponsors(FileId);


GO
