/* =========================================================
   Step 1.10 - Actual Row Counts
   ========================================================= */

CREATE TABLE #TableRowCounts
(
    SchemaName SYSNAME,
    TableName SYSNAME,
    ActualRowCount BIGINT
);

DECLARE
    @Schema SYSNAME,
    @Table SYSNAME,
    @SQL NVARCHAR(MAX);

DECLARE TableCursor CURSOR LOCAL FAST_FORWARD FOR
SELECT
    s.name,
    t.name
FROM sys.tables AS t
INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id
WHERE
    t.is_ms_shipped = 0
ORDER BY
    s.name,
    t.name;

OPEN TableCursor;

FETCH NEXT FROM TableCursor INTO @Schema, @Table;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @SQL = N'
        INSERT INTO #TableRowCounts
        SELECT
            @pSchema,
            @pTable,
            COUNT_BIG(*)
        FROM ' + QUOTENAME(@Schema) + N'.'
                 + QUOTENAME(@Table) + N';';

    EXEC sys.sp_executesql
        @SQL,
        N'@pSchema SYSNAME, @pTable SYSNAME',
        @pSchema = @Schema,
        @pTable = @Table;

    FETCH NEXT FROM TableCursor INTO @Schema, @Table;
END;

CLOSE TableCursor;
DEALLOCATE TableCursor;

SELECT *
FROM #TableRowCounts
ORDER BY ActualRowCount DESC;

DROP TABLE #TableRowCounts;