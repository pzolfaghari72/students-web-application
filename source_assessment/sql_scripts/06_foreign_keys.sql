/* =========================================================
   Step 1.6 - Foreign Key Relationships
   ========================================================= */

SELECT
    ps.name AS ParentSchema,
    pt.name AS ParentTable,
    pc.name AS ParentColumn,

    rs.name AS ReferencedSchema,
    rt.name AS ReferencedTable,
    rc.name AS ReferencedColumn,

    fk.name AS ForeignKeyName,
    fkc.constraint_column_id AS ColumnOrdinal,

    fk.is_disabled AS IsDisabled,
    fk.is_not_trusted AS IsNotTrusted,

    fk.delete_referential_action_desc AS DeleteAction,
    fk.update_referential_action_desc AS UpdateAction

FROM sys.foreign_keys AS fk

INNER JOIN sys.foreign_key_columns AS fkc
    ON fkc.constraint_object_id = fk.object_id

INNER JOIN sys.tables AS pt
    ON pt.object_id = fkc.parent_object_id

INNER JOIN sys.schemas AS ps
    ON ps.schema_id = pt.schema_id

INNER JOIN sys.columns AS pc
    ON pc.object_id = pt.object_id
   AND pc.column_id = fkc.parent_column_id

INNER JOIN sys.tables AS rt
    ON rt.object_id = fkc.referenced_object_id

INNER JOIN sys.schemas AS rs
    ON rs.schema_id = rt.schema_id

INNER JOIN sys.columns AS rc
    ON rc.object_id = rt.object_id
   AND rc.column_id = fkc.referenced_column_id

ORDER BY
    ps.name,
    pt.name,
    fk.name,
    fkc.constraint_column_id;