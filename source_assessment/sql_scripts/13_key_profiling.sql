/* =========================================================
   Step 1.13 - Key Candidate Profiling
   ========================================================= */

DROP TABLE IF EXISTS #DuplicateProfiling;

CREATE TABLE #DuplicateProfiling
(
    SchemaName SYSNAME,
    TableName SYSNAME,
    ColumnName SYSNAME,
    TotalRows BIGINT,
    NullCount BIGINT,
    DistinctNonNullValues BIGINT,
    DuplicateExcessRows BIGINT
);

DECLARE
    @SchemaName2 SYSNAME,
    @TableName2 SYSNAME,
    @ColumnName2 SYSNAME,
    @SQL2 NVARCHAR(MAX);

DECLARE KeyCandidateCursor CURSOR LOCAL FAST_FORWARD FOR
SELECT
    s.name,
    t.name,
    c.name
FROM sys.tables AS t
INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id
INNER JOIN sys.columns AS c
    ON c.object_id = t.object_id
WHERE
    t.is_ms_shipped = 0
    AND t.name <> 'sysdiagrams'
    AND (
        c.name LIKE '%Id'
        OR c.name = 'StudentId'
    )
    AND c.is_computed = 0
ORDER BY
    s.name,
    t.name,
    c.column_id;

OPEN KeyCandidateCursor;

FETCH NEXT FROM KeyCandidateCursor
INTO @SchemaName2, @TableName2, @ColumnName2;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @SQL2 = N'
        INSERT INTO #DuplicateProfiling
        SELECT
            @pSchema,
            @pTable,
            @pColumn,
            COUNT_BIG(*),
            COUNT_BIG(*) - COUNT_BIG('
                + QUOTENAME(@ColumnName2) + N'),
            COUNT_BIG(DISTINCT '
                + QUOTENAME(@ColumnName2) + N'),
            COUNT_BIG('
                + QUOTENAME(@ColumnName2) + N')
                - COUNT_BIG(DISTINCT '
                + QUOTENAME(@ColumnName2) + N')
        FROM '
        + QUOTENAME(@SchemaName2) + N'.'
        + QUOTENAME(@TableName2) + N';';

    EXEC sys.sp_executesql
        @SQL2,
        N'@pSchema SYSNAME, @pTable SYSNAME, @pColumn SYSNAME',
        @pSchema = @SchemaName2,
        @pTable = @TableName2,
        @pColumn = @ColumnName2;

    FETCH NEXT FROM KeyCandidateCursor
    INTO @SchemaName2, @TableName2, @ColumnName2;
END;

CLOSE KeyCandidateCursor;
DEALLOCATE KeyCandidateCursor;

SELECT *
FROM #DuplicateProfiling
ORDER BY
    TableName,
    DuplicateExcessRows DESC,
    ColumnName;

DROP TABLE #DuplicateProfiling;