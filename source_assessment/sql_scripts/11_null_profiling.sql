/* =========================================================
   Step 1.11 - Null Profiling
   ========================================================= */

DROP TABLE IF EXISTS #NullProfiling;

CREATE TABLE #NullProfiling
(
    SchemaName SYSNAME,
    TableName SYSNAME,
    ColumnName SYSNAME,
    TotalRows BIGINT,
    NullCount BIGINT,
    NonNullCount BIGINT,
    NullPercentage DECIMAL(9, 2)
);

DECLARE
    @SchemaName SYSNAME,
    @TableName SYSNAME,
    @ColumnName SYSNAME,
    @SQL NVARCHAR(MAX);

DECLARE ColumnCursor CURSOR LOCAL FAST_FORWARD FOR
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
ORDER BY
    s.name,
    t.name,
    c.column_id;

OPEN ColumnCursor;

FETCH NEXT FROM ColumnCursor
INTO @SchemaName, @TableName, @ColumnName;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @SQL = N'
        INSERT INTO #NullProfiling
        (
            SchemaName,
            TableName,
            ColumnName,
            TotalRows,
            NullCount,
            NonNullCount,
            NullPercentage
        )
        SELECT
            @pSchema,
            @pTable,
            @pColumn,
            COUNT_BIG(*),
            COUNT_BIG(*) - COUNT_BIG('
                + QUOTENAME(@ColumnName) + N'),
            COUNT_BIG(' + QUOTENAME(@ColumnName) + N'),
            CAST(
                100.0 *
                (COUNT_BIG(*) - COUNT_BIG('
                    + QUOTENAME(@ColumnName) + N'))
                / NULLIF(COUNT_BIG(*), 0)
                AS DECIMAL(9, 2)
            )
        FROM '
        + QUOTENAME(@SchemaName) + N'.'
        + QUOTENAME(@TableName) + N';';

    EXEC sys.sp_executesql
        @SQL,
        N'@pSchema SYSNAME, @pTable SYSNAME, @pColumn SYSNAME',
        @pSchema = @SchemaName,
        @pTable = @TableName,
        @pColumn = @ColumnName;

    FETCH NEXT FROM ColumnCursor
    INTO @SchemaName, @TableName, @ColumnName;
END;

CLOSE ColumnCursor;
DEALLOCATE ColumnCursor;

SELECT *
FROM #NullProfiling
ORDER BY
    TableName,
    NullPercentage DESC,
    ColumnName;

DROP TABLE #NullProfiling;