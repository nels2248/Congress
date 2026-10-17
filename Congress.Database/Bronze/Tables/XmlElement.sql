CREATE TABLE [Bronze].[XmlElement] (
    [ElementId]       BIGINT          IDENTITY (1, 1) NOT NULL,
    [FileId]          INT             NOT NULL,
    [ParentElementId] BIGINT          NULL,
    [XmlPath]         NVARCHAR (2000) NOT NULL,
    [ElementName]     NVARCHAR (500)  NOT NULL,
    [Occurrence]      INT             NOT NULL,
    PRIMARY KEY CLUSTERED ([ElementId] ASC),
    CONSTRAINT [FK_XmlElement_File] FOREIGN KEY ([FileId]) REFERENCES [Bronze].[XmlFile] ([FileId]),
    CONSTRAINT [FK_XmlElement_Parent] FOREIGN KEY ([ParentElementId]) REFERENCES [Bronze].[XmlElement] ([ElementId])
);


GO

CREATE NONCLUSTERED INDEX [IX_XmlElement_ParentElementId]
    ON [Bronze].[XmlElement]([ParentElementId] ASC);


GO

CREATE NONCLUSTERED INDEX [IX_XmlElement_XmlPath]
    ON [Bronze].[XmlElement]([XmlPath] ASC);


GO

CREATE NONCLUSTERED INDEX [IX_XmlElement_FileId]
    ON [Bronze].[XmlElement]([FileId] ASC);


GO

