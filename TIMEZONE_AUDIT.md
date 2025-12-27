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

## ⚠️ NEEDS REVIEW: Transform Script (`transform_bronze_to_gold.py`)

### Silver Layer Transformation

**Line 99:** Transaction date passthrough
```sql
b.date as transaction_date,
```
**Status:** ⚠️ DEPENDS - If bronze.sales_transactions.date is already PST (from Square connector), this is fine

**Lines 103-106:** Time extractions from transaction_date
```sql
EXTRACT(HOUR FROM b.date) as transaction_hour,
EXTRACT(DOW FROM b.date) as transaction_day_of_week,
EXTRACT(MONTH FROM b.date) as transaction_month,
EXTRACT(YEAR FROM b.date) as transaction_year
```
**Status:** ⚠️ DEPENDS - If b.date is timezone-aware PST, needs AT TIME ZONE
**Recommended Fix:**
```sql
EXTRACT(HOUR FROM (b.date AT TIME ZONE 'America/Los_Angeles')) as transaction_hour,
EXTRACT(DOW FROM (b.date AT TIME ZONE 'America/Los_Angeles')) as transaction_day_of_week,
```

### Gold Layer Transformation

**Line 202:** Date key generation from silver
```sql
TO_CHAR(t.transaction_date, 'YYYYMMDD')::INTEGER as date_key,
```
**Status:** ⚠️ POTENTIAL ISSUE - Should convert to PST explicitly
**Recommended Fix:**
```sql
TO_CHAR(t.transaction_date AT TIME ZONE 'America/Los_Angeles', 'YYYYMMDD')::INTEGER as date_key,
```

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

## 📋 Recommended Actions

### High Priority
1. ✅ **DONE:** Fix `sync_square_to_postgres.py` date_key generation (Line 440)
2. ⚠️ **TODO:** Check bronze.sales_transactions schema for timezone awareness
3. ⚠️ **TODO:** Fix `transform_bronze_to_gold.py` date_key generation (Line 202)
4. ⚠️ **TODO:** Add timezone conversion to silver time extractions (Lines 103-106)

### Medium Priority
5. **TODO:** Verify all date columns use consistent timezone storage
6. **TODO:** Add timezone validation tests

### Documentation
7. **TODO:** Document timezone conventions in README:
   - All dates stored in PST
   - API calls use UTC
   - Transformations explicitly convert to PST

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
