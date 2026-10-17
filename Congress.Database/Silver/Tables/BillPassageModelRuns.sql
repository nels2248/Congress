CREATE TABLE [Silver].[BillPassageModelRuns] (
    [ModelRunId]           BIGINT         IDENTITY (1, 1) NOT NULL,
    [RunAt]                DATETIME2 (7)  CONSTRAINT [DF_BillPassageModelRuns_RunAt] DEFAULT (sysutcdatetime()) NOT NULL,
    [BillCount]            INT            NULL,
    [BecameLawCount]       INT            NULL,
    [DidNotBecomeLawCount] INT            NULL,
    [TrainingCount]        INT            NULL,
    [TestCount]            INT            NULL,
    [Accuracy]             FLOAT (53)     NULL,
    [AUC]                  FLOAT (53)     NULL,
    [ModelType]            NVARCHAR (200) NULL,
    [Intercept]            FLOAT (53)     NULL,
    PRIMARY KEY CLUSTERED ([ModelRunId] ASC)
);


GO

