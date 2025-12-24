-- Check the structure and constraints of demand_forecasts table
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'predictions'
  AND table_name = 'demand_forecasts'
ORDER BY ordinal_position;

-- Check unique constraints
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'predictions'
  AND tc.table_name = 'demand_forecasts'
ORDER BY tc.constraint_type, kcu.ordinal_position;
