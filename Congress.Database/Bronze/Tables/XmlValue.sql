CREATE TABLE [Bronze].[XmlValue] (
    [ValueId]   BIGINT          IDENTITY (1, 1) NOT NULL,
    [ElementId] BIGINT          NOT NULL,
    [XmlPath]   NVARCHAR (2000) NOT NULL,
    [Value]     NVARCHAR (MAX)  NULL,
    [DataType]  VARCHAR (50)    NULL,
    PRIMARY KEY CLUSTERED ([ValueId] ASC),
    CONSTRAINT [FK_XmlValue_Element] FOREIGN KEY ([ElementId]) REFERENCES [Bronze].[XmlElement] ([ElementId])
);


GO

CREATE NONCLUSTERED INDEX [IX_XmlValue_XmlPath_Covering]
    ON [Bronze].[XmlValue]([XmlPath] ASC)
    INCLUDE([ElementId], [Value]);


GO

CREATE NONCLUSTERED INDEX [IX_XmlValue_ElementId]
    ON [Bronze].[XmlValue]([ElementId] ASC);


GO

CREATE NONCLUSTERED INDEX [IX_XmlValue_ElementId_XmlPath]
    ON [Bronze].[XmlValue]([ElementId] ASC, [XmlPath] ASC)
    INCLUDE([Value]);


GO

