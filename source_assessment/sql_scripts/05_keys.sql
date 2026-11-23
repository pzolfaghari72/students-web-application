/* =========================================================
   Step 1.5 - Primary Unique Keys
   ========================================================= */

SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    kc.name AS ConstraintName,
    kc.type_desc AS ConstraintType,
    c.name AS ColumnName,
    ic.key_ordinal AS KeyOrdinal,
    ic.is_descending_key AS IsDescending
FROM sys.key_constraints AS kc
INNER JOIN sys.tables AS t
    ON t.object_id = kc.parent_object_id
INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id
INNER JOIN sys.index_columns AS ic
    ON ic.object_id = t.object_id
    AND ic.index_id = kc.unique_index_id
INNER JOIN sys.columns AS c
    ON c.object_id = t.object_id
    AND c.column_id = ic.column_id
ORDER BY
    s.name,
    t.name,
    kc.name,
    ic.key_ordinal;