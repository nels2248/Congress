CREATE TABLE [Silver].[BillPassagePredictions] (
    [PredictionId]         BIGINT          IDENTITY (1, 1) NOT NULL,
    [Type]                 VARCHAR (20)    NOT NULL,
    [BillNumber]           INT             NOT NULL,
    [Title]                NVARCHAR (1000) NULL,
    [ActualBecameLaw]      BIT             NULL,
    [PredictedProbability] FLOAT (53)      NULL,
    [PredictedOutcome]     NVARCHAR (50)   NULL,
    [PredictionRunId]      BIGINT          NULL,
    [RunAt]                DATETIME2 (7)   CONSTRAINT [DF_BillPassagePredictions_RunAt] DEFAULT (sysutcdatetime()) NOT NULL,
    PRIMARY KEY CLUSTERED ([PredictionId] ASC)
);


GO

CREATE UNIQUE NONCLUSTERED INDEX [UX_BillPassagePredictions_BillRun]
    ON [Silver].[BillPassagePredictions]([Type] ASC, [BillNumber] ASC, [PredictionRunId] ASC);


GO

