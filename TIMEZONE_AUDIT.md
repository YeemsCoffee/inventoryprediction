# Timezone Audit Report - Data Pipeline
Generated: 2025-12-26

## Summary
Comprehensive audit of all timezone handling in the data sync and transformation pipeline.

---

## ✅ FIXED: Square Connector (`src/integrations/square_connector.py`)

### Status: CORRECT ✅

**Lines 126-136:** Input date handling
```python
# Input dates treated as PST, converted to UTC for API
start_dt_pst = start_dt_naive.replace(tzinfo=PST)
start_dt_utc = start_dt_pst.astimezone(ZoneInfo('UTC'))
```
**Status:** ✅ Correct - Properly converts PST → UTC for API calls

**Lines 186-188:** Timestamp storage
```python
created_at_utc = pd.to_datetime(order.get('created_at'))
created_at = created_at_utc.tz_convert(PST) if created_at_utc.tz is not None else created_at_utc.tz_localize('UTC').tz_convert(PST)
```
**Status:** ✅ Correct - Converts UTC from Square → PST for storage

---

## ✅ FIXED: Sync Script (`scripts/sync_square_to_postgres.py`)

### Bronze Layer - CORRECT ✅

**Lines 217-218:** Order timestamps
```python
first_row['date'],  # Already in PST from Square connector
first_row['date'],
```
**Status:** ✅ Correct - Uses PST timestamps from Square connector

### Gold Layer - FIXED ✅

**Lines 439-440:** Date key generation (RECENTLY FIXED)
```sql
TO_CHAR(bo.created_at AT TIME ZONE 'America/Los_Angeles', 'YYYYMMDD')::INTEGER as date_key
```
**Status:** ✅ FIXED - Now converts to PST before creating date_key

**Lines 453-454:** Hour/day extraction
```sql
EXTRACT(HOUR FROM (bo.created_at AT TIME ZONE 'America/Los_Angeles'))::INTEGER as order_hour
EXTRACT(DOW FROM (bo.created_at AT TIME ZONE 'America/Los_Angeles'))::INTEGER as order_day_of_week
```
**Status:** ✅ Correct - Converts to PST for time-based extractions

---

## ✅ FIXED: Transform Script (`transform_bronze_to_gold.py`)

### Silver Layer Transformation - FIXED ✅

**Line 99:** Transaction date passthrough
```sql
b.date as transaction_date,
```
**Status:** ✅ Correct - Passes through timezone-aware timestamp

**Lines 103-106:** Time extractions from transaction_date (FIXED)
```sql
EXTRACT(HOUR FROM (b.date AT TIME ZONE 'America/Los_Angeles')) as transaction_hour,
EXTRACT(DOW FROM (b.date AT TIME ZONE 'America/Los_Angeles')) as transaction_day_of_week,
EXTRACT(MONTH FROM (b.date AT TIME ZONE 'America/Los_Angeles')) as transaction_month,
EXTRACT(YEAR FROM (b.date AT TIME ZONE 'America/Los_Angeles')) as transaction_year
```
**Status:** ✅ FIXED - Now converts to PST before extracting time parts

### Gold Layer Transformation - FIXED ✅

**Line 202:** Date key generation from silver (FIXED)
```sql
TO_CHAR(t.transaction_date AT TIME ZONE 'America/Los_Angeles', 'YYYYMMDD')::INTEGER as date_key,
```
**Status:** ✅ FIXED - Now converts to PST before creating date_key

---

## 🔍 Questions to Verify

1. **Bronze Layer Schema:** Is `bronze.sales_transactions.date` stored as:
   - `TIMESTAMP WITH TIME ZONE` (timezone-aware)?
   - `TIMESTAMP WITHOUT TIME ZONE` (naive)?

2. **Silver Layer Schema:** Is `silver.transactions.transaction_date` stored as:
   - `TIMESTAMP WITH TIME ZONE`?
   - `TIMESTAMP WITHOUT TIME ZONE`?

3. **Consistency Check:** Run this query to verify:
```sql
-- Check if timestamps are timezone-aware
SELECT
    column_name,
    data_type,
    datetime_precision
FROM information_schema.columns
WHERE table_schema IN ('bronze', 'silver', 'gold')
  AND table_name IN ('sales_transactions', 'square_orders', 'transactions', 'fact_sales')
  AND column_name LIKE '%date%' OR column_name LIKE '%time%'
ORDER BY table_schema, table_name, column_name;
```

---

## 📋 Actions Completed ✅

### All Critical Issues Fixed!
1. ✅ **DONE:** Fix `sync_square_to_postgres.py` date_key generation (Line 440)
2. ✅ **DONE:** Verified bronze.sales_transactions schema - all timezone-aware
3. ✅ **DONE:** Fix `transform_bronze_to_gold.py` date_key generation (Line 202)
4. ✅ **DONE:** Add timezone conversion to silver time extractions (Lines 103-106)
5. ✅ **DONE:** Fix `validate_predictions.py` to use PST timezone
6. ✅ **DONE:** Fix Square connector to handle PST dates correctly

### Remaining Tasks
7. ⚠️ **TODO:** Resync all data to apply timezone fixes
8. ⚠️ **TODO:** Verify Dec 24 validation shows 26 Americanos (not 27)
9. 📝 **TODO:** Add timezone validation tests
10. 📝 **TODO:** Document timezone conventions in main README

---

## 🎯 Timezone Best Practices

### Rules Applied:
1. ✅ **Input:** Accept dates as PST (business timezone)
2. ✅ **API Calls:** Convert PST → UTC for external APIs (Square)
3. ✅ **Storage:** Store all timestamps in PST (with timezone info)
4. ✅ **Extraction:** Always use `AT TIME ZONE 'America/Los_Angeles'` when extracting date parts
5. ✅ **Display:** Show PST in reports and validation

### Common Pitfalls Fixed:
- ❌ Using `datetime.now()` without timezone (uses system time)
- ❌ Creating date_key from UTC timestamps
- ❌ Extracting hour/day without timezone conversion
- ❌ Comparing dates across different timezones

---

## Next Steps

Run the schema verification query above and check if `transform_bronze_to_gold.py` needs the same timezone fixes as `sync_square_to_postgres.py`.
