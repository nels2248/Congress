CREATE TABLE [Silver].[BillPassageReasons] (
    [ReasonId]        BIGINT         IDENTITY (1, 1) NOT NULL,
    [Type]            VARCHAR (20)   NOT NULL,
    [BillNumber]      INT            NOT NULL,
    [FeatureName]     NVARCHAR (255) NOT NULL,
    [Contribution]    FLOAT (53)     NULL,
    [Direction]       NVARCHAR (20)  NOT NULL,
    [ReasonRank]      INT            NOT NULL,
    [PredictionRunId] BIGINT         NULL,
    [RunAt]           DATETIME2 (7)  CONSTRAINT [DF_BillPassageReasons_RunAt] DEFAULT (sysutcdatetime()) NOT NULL,
    PRIMARY KEY CLUSTERED ([ReasonId] ASC)
);


GO

CREATE NONCLUSTERED INDEX [IX_BillPassageReasons_BillRun]
    ON [Silver].[BillPassageReasons]([Type] ASC, [BillNumber] ASC, [PredictionRunId] ASC);


GO

