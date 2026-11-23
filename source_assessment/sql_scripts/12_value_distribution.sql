/* =========================================================
   Step 1.12 - value Distribution
   ========================================================= */

SELECT
    'Students' AS TableName,
    'StudentStatus' AS ColumnName,
    CAST(StudentStatus AS NVARCHAR(4000)) AS Value,
    COUNT_BIG(*) AS RecordCount
FROM dbo.Students
GROUP BY StudentStatus

UNION ALL

SELECT
    'Students',
    'ClassStandingCode',
    CAST(ClassStandingCode AS NVARCHAR(4000)),
    COUNT_BIG(*)
FROM dbo.Students
GROUP BY ClassStandingCode

UNION ALL

SELECT
    'CourseEnrollments',
    'Grade',
    CAST(Grade AS NVARCHAR(4000)),
    COUNT_BIG(*)
FROM dbo.CourseEnrollments
GROUP BY Grade

UNION ALL

SELECT
    'Grades',
    'Grade',
    CAST(Grade AS NVARCHAR(4000)),
    COUNT_BIG(*)
FROM dbo.Grades
GROUP BY Grade

ORDER BY
    TableName,
    ColumnName,
    RecordCount DESC;