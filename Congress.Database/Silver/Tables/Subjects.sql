CREATE TABLE [Silver].[Subjects] (
    Type        VARCHAR(20)  NOT NULL,
    BillNumber  INT          NOT NULL,
    SubjectType VARCHAR(30)  NOT NULL,
    SubjectName VARCHAR(300) NOT NULL,
    FileId      INT          NOT NULL
);


GO

CREATE UNIQUE CLUSTERED INDEX IX_Silver_Subjects_BillSubject ON Silver.Subjects(Type, BillNumber, SubjectType, SubjectName);


GO

CREATE INDEX IX_Silver_Subjects_SubjectName ON Silver.Subjects(SubjectName);


GO
