# PostgreSQL Migration Guide

Complete guide to migrating from CSV to PostgreSQL for production-scale analytics.

## 📋 Table of Contents

1. [Why PostgreSQL?](#why-postgresql)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Quick Start](#quick-start)
5. [Detailed Steps](#detailed-steps)
6. [Troubleshooting](#troubleshooting)

---

## Why PostgreSQL?

At your scale (2-3K orders/day across 2 locations), CSV files have limitations:

| Aspect | CSV | PostgreSQL |
|--------|-----|------------|
| **Query Speed** | Slow (full scan) | Fast (indexed) |
| **Concurrent Access** | File locks | Multi-user |
| **Data Size** | <100MB recommended | TBs supported |
| **Data Integrity** | None | ACID transactions |
| **Incremental Updates** | Replace whole file | Update specific rows |
| **Partitioning** | Manual | Automatic |

**Your benefits:**
- 10-100x faster queries on historical data
- Support for years of transaction history
- Incremental syncs (only new data)
- Better data quality and integrity

---

## Architecture Overview

### Medallion Architecture (Bronze → Silver → Gold)

```
┌─────────────────────────────────────────────────────────────┐
│ SQUARE API                                                   │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ BRONZE LAYER - Raw Immutable Data                           │
│  • bronze.square_orders                                      │
│  • bronze.square_line_items                                  │
│  • bronze.square_customers                                   │
│  • Full API payloads stored as JSONB                         │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ SILVER LAYER - Cleaned & Typed                              │
│  • silver.orders (partitioned by quarter)                    │
│  • silver.line_items                                         │
│  • silver.customers (SCD Type 2)                             │
│  • silver.products                                           │
│  • silver.locations                                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ GOLD LAYER - Analytics-Ready Star Schema                    │
│  • gold.dim_customer (SCD Type 2)                            │
│  • gold.dim_product                                          │
│  • gold.dim_location                                         │
│  • gold.dim_date (pre-populated 2020-2030)                   │
│  • gold.fact_sales (partitioned by year)                     │
│  • Materialized views for performance                        │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ FEATURES LAYER - ML Features                                 │
│  • features.customer_daily_features                          │
│  • features.product_location_daily_features                  │
│  • Point-in-time correctness for training                    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ PREDICTIONS LAYER - ML Outputs                               │
│  • predictions.customer_churn_scores                         │
│  • predictions.demand_forecasts                              │
│  • predictions.customer_ltv_scores                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### 1. PostgreSQL Database

Choose one option:

#### **Option A: Local PostgreSQL (Development)**

**Windows:**
```powershell
# Download from postgresql.org
# Or use Chocolatey:
choco install postgresql

# Start service
net start postgresql
```

**Mac:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux:**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

#### **Option B: Managed PostgreSQL (Recommended for Production)**

| Provider | Cost (Small) | Setup Time | Notes |
|----------|--------------|------------|-------|
| **Supabase** | Free tier | 5 min | Easy, includes dashboard |
| **Railway** | $5/month | 5 min | Simple, good for startups |
| **DigitalOcean** | $15/month | 10 min | Reliable, well-documented |
| **AWS RDS** | $30/month | 15 min | Enterprise-grade |
| **Heroku Postgres** | $9/month | 5 min | Easy if using Heroku |

**Recommended: Railway or Supabase** for ease of use.

### 2. Create Database

```bash
# Local PostgreSQL
createdb inventory_bi

# Or using psql
psql -U postgres
CREATE DATABASE inventory_bi;
\q
```

For managed providers, create database through their web console.

### 3. Install Python Dependencies

```powershell
# Activate your virtual environment
venv\Scripts\activate

# Install new dependencies
pip install -r requirements.txt
```

---

## Quick Start

### Step 1: Configure Database URL

Add to your `.env` file:

```bash
# PostgreSQL Connection
DATABASE_URL=postgresql://username:password@localhost:5432/inventory_bi

# For managed services, use their connection string:
# Railway: postgresql://user:pass@containers-us-west-xxx.railway.app:5432/railway
# Supabase: postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres
```

### Step 2: Initialize Database Schema

```powershell
# Run schema setup
python database/init_database.py
```

This creates all tables (Bronze, Silver, Gold, Features, Predictions).

### Step 3: Migrate Historical CSV Data

```powershell
# Migrate your existing CSV data to PostgreSQL
python scripts/migrate_csv_to_postgres.py
```

**What this does:**
- Loads your CSV file
- Populates Bronze layer (raw)
- Transforms to Silver layer (cleaned)
- Creates Gold layer (analytics star schema)
- Refreshes materialized views

**Time:** ~5-30 minutes depending on data volume

### Step 4: Set Up Incremental Sync

```powershell
# Test incremental sync from Square
python scripts/sync_square_to_postgres.py
```

### Step 5: Update Dashboard

```powershell
# Dashboard now reads from PostgreSQL
python start_production.py
```

**Much faster queries!** 🚀

---

## Detailed Steps

### Database Schema Explained

#### Bronze Layer
- **Purpose:** Store raw, immutable data from Square API
- **Format:** JSONB columns for full API responses
- **Use:** Data lineage, debugging, reprocessing

#### Silver Layer
- **Purpose:** Cleaned, typed, business-ready data
- **Features:**
  - Partitioning for performance (orders by quarter)
  - SCD Type 2 for tracking customer changes
  - Data quality constraints
- **Use:** Reliable data for downstream processing

#### Gold Layer
- **Purpose:** Analytics-ready dimensional model
- **Features:**
  - Star schema (facts + dimensions)
  - Surrogate keys for performance
  - Materialized views for common queries
  - Partitioned by year
- **Use:** BI dashboards, reporting

#### Features Layer
- **Purpose:** ML-ready feature tables
- **Features:**
  - Point-in-time correctness (no data leakage)
  - Daily snapshots of features
  - Ready for model training/inference
- **Use:** Machine learning models

#### Predictions Layer
- **Purpose:** Store ML model outputs
- **Features:**
  - Model versioning
  - Confidence scores
  - Prediction timestamps
- **Use:** Operational decision-making

### Partitioning Strategy

Large tables are partitioned for query performance:

```sql
-- fact_sales partitioned by year
fact_sales_2023 (date_key >= 20230101 AND date_key < 20240101)
fact_sales_2024 (date_key >= 20240101 AND date_key < 20250101)
fact_sales_2025 (date_key >= 20250101 AND date_key < 20260101)
```

**Benefits:**
- Queries only scan relevant partitions
- Faster inserts and deletes
- Easier archival of old data

### Indexes

Strategic indexes for common query patterns:

```sql
-- Date range queries
CREATE INDEX idx_fact_sales_date ON gold.fact_sales(date_key);

-- Customer analysis
CREATE INDEX idx_fact_sales_customer ON gold.fact_sales(customer_sk, date_key);

-- Product performance
CREATE INDEX idx_fact_sales_product ON gold.fact_sales(product_sk, date_key);

-- Location analytics
CREATE INDEX idx_fact_sales_location ON gold.fact_sales(location_sk, date_key);
```

---

## Configuration

### Environment Variables

Add to `.env`:

```bash
# PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/database
CSV_DATA_PATH=data/raw/square_sales.csv

# Square API (existing)
SQUARE_ACCESS_TOKEN=your_token
SQUARE_ENVIRONMENT=production

# Dashboard (existing)
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8050
```

### Connection String Format

```
postgresql://[user]:[password]@[host]:[port]/[database]?[options]
```

**Examples:**

```bash
# Local
DATABASE_URL=postgresql://postgres:password@localhost:5432/inventory_bi

# Railway
DATABASE_URL=postgresql://postgres:pass@containers-us-west-123.railway.app:5432/railway

# Supabase
DATABASE_URL=postgresql://postgres:pass@db.abcdefghijklm.supabase.co:5432/postgres

# With SSL (often required for managed databases)
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

---

## Troubleshooting

### Connection Issues

**Error:** `could not connect to server`

**Solution:**
1. Check PostgreSQL is running: `pg_isready`
2. Verify host/port in DATABASE_URL
3. Check firewall allows port 5432
4. For managed databases, check IP whitelist

**Error:** `password authentication failed`

**Solution:**
1. Verify username/password in DATABASE_URL
2. For local PostgreSQL, check `pg_hba.conf`
3. Reset password if needed: `ALTER USER postgres PASSWORD 'newpass';`

### Migration Issues

**Error:** `relation "bronze.square_orders" does not exist`

**Solution:**
Run schema initialization first:
```powershell
python database/init_database.py
```

**Error:** `could not open file "...csv": No such file or directory`

**Solution:**
Set correct CSV path in .env:
```bash
CSV_DATA_PATH=data/raw/square_sales.csv
```

**Error:** Migration is very slow

**Solution:**
1. Check you have good network connection to database
2. For large datasets (>1M rows), consider:
   - Running migration on same network as database
   - Using COPY instead of INSERT (advanced)
   - Temporarily disabling indexes during bulk load

### Performance Issues

**Slow queries after migration**

**Solution:**
1. Ensure partitions were created correctly
2. Refresh materialized views:
   ```sql
   REFRESH MATERIALIZED VIEW CONCURRENTLY gold.daily_sales_summary;
   REFRESH MATERIALIZED VIEW CONCURRENTLY gold.product_performance;
   ```
3. Run VACUUM ANALYZE:
   ```sql
   VACUUM ANALYZE gold.fact_sales;
   ```

---

## Next Steps After Migration

### 1. Set Up dbt (Coming Next)

dbt will manage your transformations from Bronze → Silver → Gold.

**Benefits:**
- Version control your SQL
- Test data quality
- Document your metrics
- Incremental models

### 2. Add Dagster Orchestration (Coming Next)

Dagster will schedule and monitor your data pipelines.

**Benefits:**
- Automated daily syncs
- Retry failed jobs
- Data lineage visualization
- Alert on failures

### 3. Add Data Quality Tests (Coming Next)

Great Expectations will validate your data.

**Benefits:**
- Catch bad data early
- Document expectations
- Track data quality over time

---

## Cost Estimates

### Monthly Costs by Scale

| Data Volume | Orders/Day | Database Size | Recommended | Cost |
|-------------|------------|---------------|-------------|------|
| Small | <500 | <5GB | Railway/Supabase | $5-10 |
| **Your Scale** | **2-3K** | **10-50GB** | **DigitalOcean** | **$15-30** |
| Large | 10K+ | 100GB+ | AWS RDS | $50-200 |
| Enterprise | 50K+ | 500GB+ | AWS RDS Multi-AZ | $200-1000 |

**Your recommended setup:**
- DigitalOcean Managed PostgreSQL: $15/month
- 2 vCPU, 2GB RAM, 50GB storage
- Automated backups included
- Easy vertical scaling

---

## Support

### Common Questions

**Q: Can I keep using CSV for development?**
A: Yes! The app still supports CSV. PostgreSQL is for production.

**Q: Do I need to run migration again if I add more Square data?**
A: No. Use the incremental sync script instead.

**Q: Can I query PostgreSQL directly?**
A: Yes! Use any SQL client (DBeaver, pgAdmin, etc.)

**Q: Will this break my existing dashboard?**
A: No. We'll update the app to read from PostgreSQL, but CSV still works.

---

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [dbt Documentation](https://docs.getdbt.com/)
- [Dagster Documentation](https://docs.dagster.io/)
- [Great Expectations](https://greatexpectations.io/)

---

**Ready to get started?** Follow the Quick Start guide above!
