# Database Setup Instructions

## ⚠️ Important: Network Connectivity Issue

The cloud development environment cannot reach your AWS RDS instance due to DNS resolution failure. **You need to run the setup script from your local machine** where you have network access to AWS.

---

## Prerequisites

1. **AWS RDS PostgreSQL** - Your instance must be:
   - Running and accessible
   - Security group configured to allow your IP address on port 5432
   - Publicly accessible (if connecting from outside VPC)

2. **Python 3.8+** with packages:
   ```bash
   pip install psycopg2-binary python-dotenv
   ```

3. **Environment Variables** - Your `.env` file must contain:
   ```
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/postgres
   ```

---

## Step-by-Step Setup

### 1. Verify RDS Connectivity

First, check that your RDS instance is reachable from your local machine:

```bash
# Test DNS resolution
python scripts/test_dns.py

# If DNS works, test database connection
python scripts/test_db_connection.py
```

**Expected output:**
```
✅ Connected to database: postgres
✅ Bronze schema exists
✅ bronze.square_orders table exists
✅ customer_id column exists
```

---

### 2. Run Complete Database Setup

If the RDS is accessible, run the comprehensive setup script:

```bash
python scripts/setup_database.py
```

**This script will:**
- ✅ Test database connection
- ✅ Create schemas (bronze, silver, gold)
- ✅ Create all Bronze layer tables (square_orders, square_line_items, etc.)
- ✅ Create Silver layer tables (sales_transactions)
- ✅ Create Gold layer tables (dim_customer, dim_product, dim_location, fact_sales)
- ✅ Add customer_id column if missing
- ✅ Create all necessary indexes

---

### 3. Create Partitions (If Needed)

If you see an error about missing partitions:

```bash
python scripts/create_partitions.py
```

This script creates partitions for `gold.fact_sales` from 2020-2027. The setup script now does this automatically, but this standalone script is available if you need to add more partitions.

---

### 4. Sync Square Data

Once the database is set up, sync your Square POS data:

```bash
# Sync oldest 90 days (3 months) of data
python scripts/sync_square_to_postgres.py --days 90 --oldest
```

**Important flags:**
- `--days 90` - Fetch 90 days of data
- `--oldest` - Start from the oldest data first (chronological order)

---

### 5. Transform Data (Bronze → Silver → Gold)

After syncing, transform the data through the layers:

```bash
python scripts/transform_data.py
```

---

### 6. Generate ML Predictions

Finally, run customer trend analysis:

```bash
python scripts/ml_customer_trends.py
```

---

## Troubleshooting

### Problem: "cannot refresh materialized view concurrently"

**Example error:**
```
cannot refresh materialized view "gold.product_performance" concurrently
HINT:  Create a unique index with no WHERE clause on one or more columns of the materialized view.
```

**Cause:** Materialized views need unique indexes to support concurrent refresh.

**Solution:**
Run the fix script:
```bash
python scripts/fix_materialized_views.py
```

This will create the missing unique indexes. Then retry the sync:
```bash
python scripts/sync_square_to_postgres.py --days 90 --oldest
```

**Note:** If you ran `setup_database.py` after this fix was added, indexes are created automatically.

---

### Problem: "no partition of relation 'fact_sales' found for row"

**Example error:**
```
no partition of relation "fact_sales" found for row
DETAIL:  Partition key of the failing row contains (date_key) = (20221224).
```

**Cause:** The `gold.fact_sales` table is partitioned by year, but no partition exists for the date in your data.

**Solution:**
Run the partition creation script:
```bash
python scripts/create_partitions.py
```

This will create partitions for years 2020-2027. Then retry the sync:
```bash
python scripts/sync_square_to_postgres.py --days 90 --oldest
```

**Note:** If you ran `setup_database.py` after this fix was added, partitions are created automatically.

---

### Problem: "could not translate host name to address"

**Cause:** DNS resolution failure - your environment cannot reach the RDS hostname.

**Solutions:**
1. Verify RDS instance is running in AWS Console
2. Check the RDS endpoint hostname is correct in your `.env` file
3. Ensure you're running from a machine with internet access
4. Try running from your local machine instead of cloud environment

---

### Problem: "pg_hba.conf rejects connection"

**Cause:** Your IP address is not whitelisted in the RDS security group.

**Solution:**
1. Go to AWS Console → RDS → Your Instance → Security Groups
2. Edit inbound rules
3. Add rule: Type=PostgreSQL, Port=5432, Source=Your IP address
4. Save changes and retry connection

---

### Problem: "customer_id column does not exist"

**Cause:** Migration was run in wrong database or didn't complete.

**Solution:**
Run the setup script which will automatically detect and add the missing column:
```bash
python scripts/setup_database.py
```

---

### Problem: "database already exists" or "table already exists"

**Cause:** Previous setup ran partially.

**Solution:**
This is normal! The setup script uses `CREATE IF NOT EXISTS` so it won't fail on existing objects. Just run it again to ensure all schemas/tables/columns exist.

---

## Verification Checklist

After running setup, verify everything is ready:

```bash
python scripts/test_db_connection.py
```

You should see:
- [x] Connected to database
- [x] Bronze schema exists
- [x] bronze.square_orders table exists
- [x] customer_id column exists

---

## Database Schema Overview

### Bronze Layer (Raw Data)
- `bronze.square_orders` - Raw orders from Square API
- `bronze.square_line_items` - Line items from orders
- `bronze.square_customers` - Customer information
- `bronze.square_locations` - Store locations
- `bronze.square_catalog_items` - Product catalog

### Silver Layer (Cleaned Data)
- `silver.sales_transactions` - Cleaned, normalized transactions

### Gold Layer (Analytics)
**Dimensions:**
- `gold.dim_customer` - Customer dimension
- `gold.dim_product` - Product dimension
- `gold.dim_location` - Location dimension
- `gold.dim_date` - Date dimension

**Facts:**
- `gold.fact_sales` - Sales fact table (star schema)

---

## Next Steps After Setup

1. **Verify data sync**:
   ```sql
   SELECT COUNT(*) FROM bronze.square_orders;
   SELECT COUNT(*) FROM bronze.square_line_items;
   SELECT MIN(created_at), MAX(created_at) FROM bronze.square_orders;
   ```

2. **Check for customer_id population**:
   ```sql
   SELECT
       customer_id,
       COUNT(*)
   FROM bronze.square_orders
   GROUP BY customer_id
   ORDER BY COUNT(*) DESC
   LIMIT 10;
   ```

3. **Run transformations** to populate Silver and Gold layers

4. **Generate ML predictions** for customer trends

---

## Support

If you continue to experience issues, please provide:
1. Output of `python scripts/test_dns.py`
2. Output of `python scripts/test_db_connection.py`
3. Your RDS endpoint from AWS Console (without password)
4. Screenshot of RDS security group inbound rules
