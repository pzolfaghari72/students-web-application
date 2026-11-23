/* =========================================================
   Step 1.2 - Table Inventory and Row Counts
   ========================================================= */

SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    SUM(ps.row_count) AS ApproximateRowCount,
    SUM(ps.reserved_page_count) * 8.0 / 1024 AS ReservedSizeMB,
    SUM(ps.used_page_count) * 8.0 / 1024 AS UsedSizeMB,
    t.create_date AS CreateDate,
    t.modify_date AS ModifyDate
FROM sys.tables AS t
INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id
LEFT JOIN sys.dm_db_partition_stats AS ps
    ON ps.object_id = t.object_id
    AND ps.index_id IN (0, 1)
GROUP BY
    s.name,
    t.name,
    t.create_date,
    t.modify_date
ORDER BY
    s.name,
    t.name;