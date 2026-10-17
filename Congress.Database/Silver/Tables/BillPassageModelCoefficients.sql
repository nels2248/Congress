CREATE TABLE [Silver].[BillPassageModelCoefficients] (
    [CoefficientId]   BIGINT         IDENTITY (1, 1) NOT NULL,
    [PredictionRunId] BIGINT         NOT NULL,
    [FeatureName]     NVARCHAR (255) NOT NULL,
    [Coefficient]     FLOAT (53)     NOT NULL,
    [RunAt]           DATETIME2 (7)  CONSTRAINT [DF_BillPassageModelCoefficients_RunAt] DEFAULT (sysutcdatetime()) NOT NULL,
    PRIMARY KEY CLUSTERED ([CoefficientId] ASC)
);


GO

CREATE NONCLUSTERED INDEX [IX_BillPassageModelCoefficients_Run]
    ON [Silver].[BillPassageModelCoefficients]([PredictionRunId] ASC);


GO

