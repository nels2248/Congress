CREATE TABLE [Silver].[Bills] (
    [BillNumber]       INT            NULL,
    [Type]             VARCHAR (20)   NULL,
    [UpdateDate]       DATE           NULL,
    [OriginChamber]    VARCHAR (50)   NULL,
    [IntroducedDate]   DATE           NULL,
    [LegislationUrl]   VARCHAR (500)  NULL,
    [PolicyArea]       VARCHAR (200)  NULL,
    [Title]            VARCHAR (2000) NULL,
    [LatestActionDate] DATE           NULL,
    [LatestAction]     VARCHAR (2000) NULL,
    [FileId]           INT            NOT NULL
);


GO

CREATE NONCLUSTERED INDEX [IX_Silver_Bills_FileId]
    ON [Silver].[Bills]([FileId] ASC);


GO

CREATE NONCLUSTERED INDEX [IX_Silver_Bills_BillNumber]
    ON [Silver].[Bills]([BillNumber] ASC);


GO

CREATE UNIQUE CLUSTERED INDEX [IX_Silver_Bills_BillId]
    ON [Silver].[Bills]([Type] ASC, [BillNumber] ASC);


GO

