/* =========================================================
   Step 1.16 - date profiling
   ========================================================= */

SELECT
    COUNT_BIG(*) AS TotalApplicants,
    SUM(CASE WHEN DateOfBirth IS NULL THEN 1 ELSE 0 END) AS NullDateOfBirth,
    MIN(DateOfBirth) AS EarliestDateOfBirth,
    MAX(DateOfBirth) AS LatestDateOfBirth
FROM dbo.Applicants;