/* =========================================================
   Step 1.4 - Object Description & Properties
   ========================================================= */

SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    CAST(ep_table.value AS NVARCHAR(4000)) AS TableDescription,
    c.name AS ColumnName,
    CAST(ep_column.value AS NVARCHAR(4000)) AS ColumnDescription
FROM sys.tables AS t
INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id
LEFT JOIN sys.extended_properties AS ep_table
    ON ep_table.major_id = t.object_id
    AND ep_table.minor_id = 0
    AND ep_table.name = 'MS_Description'
LEFT JOIN sys.columns AS c
    ON c.object_id = t.object_id
LEFT JOIN sys.extended_properties AS ep_column
    ON ep_column.major_id = c.object_id
    AND ep_column.minor_id = c.column_id
    AND ep_column.name = 'MS_Description'
ORDER BY
    s.name,
    t.name,
    c.column_id;