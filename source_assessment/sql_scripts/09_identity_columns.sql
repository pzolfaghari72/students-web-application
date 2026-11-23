/* =========================================================
   Step 1.7 - Identity Columns
   ========================================================= */

SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    c.name AS ColumnName,
    TYPE_NAME(c.user_type_id) AS DataType,
    ic.seed_value AS IdentitySeed,
    ic.increment_value AS IdentityIncrement,
    ic.last_value AS IdentityLastValue
FROM sys.identity_columns AS ic
INNER JOIN sys.tables AS t
    ON t.object_id = ic.object_id
INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id
INNER JOIN sys.columns AS c
    ON c.object_id = ic.object_id
    AND c.column_id = ic.column_id
ORDER BY
    s.name,
    t.name,
    c.column_id;