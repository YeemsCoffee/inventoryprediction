-- Verify Dec 24, 2025 data after resync
-- Run this in pgAdmin after completing the resync

-- ============================================================================
-- Check 1: Bronze layer - Orders on Dec 24, 2025
-- ============================================================================
SELECT '=== BRONZE LAYER - Dec 24, 2025 Orders ===' as check_section;

SELECT
    id,
    created_at,
    created_at AT TIME ZONE 'America/Los_Angeles' as pst_time,
    EXTRACT(HOUR FROM (created_at AT TIME ZONE 'America/Los_Angeles')) as hour_pst,
    total_money_amount,
    location_id
FROM bronze.square_orders
WHERE created_at AT TIME ZONE 'America/Los_Angeles' >= '2025-12-24 00:00:00'
  AND created_at AT TIME ZONE 'America/Los_Angeles' < '2025-12-25 00:00:00'
ORDER BY created_at;

-- ============================================================================
-- Check 2: Verify NO orders before 7 AM PST
-- ============================================================================
SELECT '=== ORDERS BEFORE 7 AM (Should be EMPTY) ===' as check_section;

SELECT
    id,
    created_at,
    created_at AT TIME ZONE 'America/Los_Angeles' as pst_time,
    EXTRACT(HOUR FROM (created_at AT TIME ZONE 'America/Los_Angeles')) as hour_pst
FROM bronze.square_orders
WHERE EXTRACT(HOUR FROM (created_at AT TIME ZONE 'America/Los_Angeles')) < 7
ORDER BY created_at
LIMIT 20;

-- ============================================================================
-- Check 3: Americano count for Dec 24, 2025 (should be exactly 26)
-- ============================================================================
SELECT '=== AMERICANO COUNT - Dec 24, 2025 ===' as check_section;

SELECT
    TRIM(SPLIT_PART(p.product_name, '(', 1)) as base_product,
    l.location_name,
    SUM(f.quantity) as total_quantity,
    COUNT(DISTINCT f.order_id) as order_count
FROM gold.fact_sales f
JOIN gold.dim_product p ON f.product_sk = p.product_sk
JOIN gold.dim_location l ON f.location_sk = l.location_sk
JOIN gold.dim_date d ON f.date_key = d.date_key
WHERE d.date = '2025-12-24'
  AND TRIM(SPLIT_PART(p.product_name, '(', 1)) = 'Americano'
GROUP BY TRIM(SPLIT_PART(p.product_name, '(', 1)), l.location_name
ORDER BY l.location_name;

-- ============================================================================
-- Check 4: Verify Dec 25 has NO sales (closed for Christmas)
-- ============================================================================
SELECT '=== DEC 25 SALES (Should be 0) ===' as check_section;

SELECT
    COUNT(*) as sales_count_dec25,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ CORRECT - No sales on Christmas'
        ELSE '❌ ERROR - Found sales on Christmas (store was closed)'
    END as validation
FROM gold.fact_sales f
JOIN gold.dim_date d ON f.date_key = d.date_key
WHERE d.date = '2025-12-25';

-- ============================================================================
-- Check 5: Date key validation - ensure date_keys match PST dates
-- ============================================================================
SELECT '=== DATE KEY VALIDATION ===' as check_section;

SELECT
    date_key,
    MIN(transaction_timestamp AT TIME ZONE 'America/Los_Angeles') as earliest_pst,
    MAX(transaction_timestamp AT TIME ZONE 'America/Los_Angeles') as latest_pst,
    TO_CHAR(MIN(transaction_timestamp AT TIME ZONE 'America/Los_Angeles'), 'YYYYMMDD')::INTEGER as expected_date_key,
    CASE
        WHEN date_key = TO_CHAR(MIN(transaction_timestamp AT TIME ZONE 'America/Los_Angeles'), 'YYYYMMDD')::INTEGER
        THEN '✅ CORRECT'
        ELSE '❌ MISMATCH'
    END as validation
FROM gold.fact_sales
WHERE date_key >= 20251220 AND date_key <= 20251226
GROUP BY date_key
ORDER BY date_key DESC;
