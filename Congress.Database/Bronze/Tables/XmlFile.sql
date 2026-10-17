CREATE TABLE [Bronze].[XmlFile] (
    [FileId]        INT             IDENTITY (1, 1) NOT NULL,
    [FileName]      NVARCHAR (500)  NOT NULL,
    [FilePath]      NVARCHAR (2000) NOT NULL,
    [FileSizeBytes] BIGINT          NULL,
    [LoadedAt]      DATETIME2 (7)   CONSTRAINT [DF_XmlFile_LoadedAt] DEFAULT (sysutcdatetime()) NOT NULL,
    PRIMARY KEY CLUSTERED ([FileId] ASC)
);


GO

CREATE NONCLUSTERED INDEX [IX_XmlFile_FilePath]
    ON [Bronze].[XmlFile]([FilePath] ASC);


GO

