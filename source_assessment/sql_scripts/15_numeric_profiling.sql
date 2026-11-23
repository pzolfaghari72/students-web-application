/* =========================================================
   Step 1.15 - Numeric Profiling
   ========================================================= */

SELECT
    COUNT_BIG(*) AS TotalCourses,
    SUM(CASE WHEN Credits IS NULL THEN 1 ELSE 0 END) AS NullCredits,
    SUM(CASE WHEN Credits <= 0 THEN 1 ELSE 0 END) AS NonPositiveCredits,
    MIN(Credits) AS MinimumCredits,
    MAX(Credits) AS MaximumCredits,
    AVG(CAST(Credits AS DECIMAL(18,4))) AS AverageCredits
FROM dbo.Courses;