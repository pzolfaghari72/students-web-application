/* =========================================================
   Step 1.7 - Index Inventory
   ========================================================= */

SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    i.name AS IndexName,

    i.type_desc AS IndexType,
    i.is_primary_key AS IsPrimaryKey,
    i.is_unique AS IsUnique,
    i.is_disabled AS IsDisabled,

    ic.key_ordinal AS KeyOrdinal,
    ic.is_included_column AS IsIncludedColumn,
    c.name AS ColumnName

FROM sys.indexes AS i

INNER JOIN sys.tables AS t
    ON t.object_id = i.object_id

INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id

INNER JOIN sys.index_columns AS ic
    ON ic.object_id = i.object_id
   AND ic.index_id = i.index_id

INNER JOIN sys.columns AS c
    ON c.object_id = t.object_id
   AND c.column_id = ic.column_id

WHERE
    i.index_id > 0
    AND i.is_hypothetical = 0

ORDER BY
    s.name,
    t.name,
    i.name,
    ic.is_included_column,
    ic.key_ordinal,
    ic.index_column_id;