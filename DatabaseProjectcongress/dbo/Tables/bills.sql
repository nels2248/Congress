CREATE TABLE [dbo].[bills] (
    [bill_id]             NVARCHAR (450) NOT NULL,
    [title]               NVARCHAR (MAX) NOT NULL,
    [sponsor]             NVARCHAR (MAX) NOT NULL,
    [passed]              BIT            NOT NULL,
    [passage_probability] FLOAT (53)     NOT NULL,
    CONSTRAINT [PK_bills] PRIMARY KEY CLUSTERED ([bill_id] ASC)
);


GO

