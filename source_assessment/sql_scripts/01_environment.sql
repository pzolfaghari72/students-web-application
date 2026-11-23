/* =========================================================
   Project: Data Warehouse
   Phase: 1 - Source System Assessment
   Step: 1.1 - Environment Inventory
   Purpose: Inspect SQL Server environment
   ========================================================= */

SELECT
    @@SERVERNAME AS ServerName,
    DB_NAME() AS DatabaseName,
    SERVERPROPERTY('ProductVersion') AS ProductVersion,
    SERVERPROPERTY('ProductLevel') AS ProductLevel,
    SERVERPROPERTY('Edition') AS Edition,
    SERVERPROPERTY('EngineEdition') AS EngineEdition,
    SYSDATETIME() AS AssessmentDateTime;