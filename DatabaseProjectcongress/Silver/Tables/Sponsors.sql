CREATE TABLE [Silver].[Sponsors] (
    [Type]        VARCHAR (20)  NULL,
    [BillNumber]  INT           NULL,
    [BioguideId]  VARCHAR (20)  NULL,
    [FullName]    VARCHAR (300) NULL,
    [FirstName]   VARCHAR (100) NULL,
    [MiddleName]  VARCHAR (100) NULL,
    [LastName]    VARCHAR (100) NULL,
    [Party]       VARCHAR (10)  NULL,
    [State]       VARCHAR (2)   NULL,
    [District]    INT           NULL,
    [IsByRequest] VARCHAR (50)  NULL,
    [FileId]      INT           NOT NULL
);


GO

CREATE UNIQUE CLUSTERED INDEX [IX_Silver_Sponsors_BillSponsor]
    ON [Silver].[Sponsors]([Type] ASC, [BillNumber] ASC, [BioguideId] ASC);


GO

CREATE NONCLUSTERED INDEX [IX_Silver_Sponsors_BioguideId]
    ON [Silver].[Sponsors]([BioguideId] ASC);


GO

CREATE NONCLUSTERED INDEX [IX_Silver_Sponsors_FileId]
    ON [Silver].[Sponsors]([FileId] ASC);


GO

