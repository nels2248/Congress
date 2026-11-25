CREATE TABLE [Silver].[Actions] (
    Type             VARCHAR(20)    NOT NULL,
    BillNumber       INT            NOT NULL,
    ActionSeq        INT            NOT NULL,
    ActionDate       DATE           NULL,
    ActionTime       VARCHAR(20)    NULL,
    ActionCode       VARCHAR(50)    NULL,
    ActionType       VARCHAR(100)   NULL,
    ActionText       NVARCHAR(MAX)  NULL,
    SourceSystemName VARCHAR(200)   NULL,
    SourceSystemCode VARCHAR(20)    NULL,
    RollNumber       INT            NULL,
    VoteChamber      VARCHAR(50)    NULL,
    VoteDate         DATE           NULL,
    VoteUrl          VARCHAR(500)   NULL,
    FileId           INT            NOT NULL
);


GO

CREATE UNIQUE CLUSTERED INDEX IX_Silver_Actions_BillSeq ON Silver.Actions(Type, BillNumber, ActionSeq);


GO
