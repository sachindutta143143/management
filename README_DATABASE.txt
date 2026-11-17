MULTI PLAZA POSTGRESQL DATABASE — CREDIT / SUPPLY COMBINED

Credit Register and Supply Register are one combined module and are stored in ONE PostgreSQL table: credit_supply_register. It has one row (id=1) whose JSON payload has two arrays: {"credit": [...], "supply": [...]}.

Backward compatibility: the existing browser endpoints /api/data/credit_register and /api/data/supply_register remain available, but both read and write their respective arrays in the same credit_supply_register row. The combined endpoint /api/data/credit_supply_register returns both arrays.

On application startup, if the combined row does not yet exist, the app migrates existing credit_register and supply_register data from app_data. If an app_data key is absent, it attempts to read id=1 from the previous dedicated table. Existing legacy app_data rows and old dedicated tables are intentionally NOT deleted. This preserves rollback/backup data.

Other modules remain in their own tables: product_list, others_register, quotation_data, installment_register, and customers.

After deploying, verify with:
SELECT id, jsonb_pretty(payload::jsonb) FROM credit_supply_register;

To count both record types from the combined JSON arrays:
SELECT jsonb_array_length(payload->'credit') AS credit_count, jsonb_array_length(payload->'supply') AS supply_count FROM credit_supply_register WHERE id=1;
