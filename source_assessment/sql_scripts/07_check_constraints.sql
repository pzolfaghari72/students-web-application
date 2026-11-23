/* =========================================================
   Step 1.7 - Check Constraints
   ========================================================= */

SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    cc.name AS ConstraintName,
    cc.definition AS ConstraintDefinition,
    cc.is_disabled AS IsDisabled,
    cc.is_not_trusted AS IsNotTrusted

FROM sys.check_constraints AS cc

INNER JOIN sys.tables AS t
    ON t.object_id = cc.parent_object_id

INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id

ORDER BY
    s.name,
    t.name,
    cc.name;