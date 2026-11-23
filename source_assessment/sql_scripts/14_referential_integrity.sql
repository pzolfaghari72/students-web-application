/* =========================================================
   Step 1.14 - referential Integrity Profiling
   ========================================================= */

SELECT
    COUNT_BIG(*) AS EnrollmentsWithoutStudent
FROM dbo.CourseEnrollments AS ce
LEFT JOIN dbo.Students AS s
    ON s.StudentId = ce.StudentId
WHERE
    s.StudentId IS NULL;
