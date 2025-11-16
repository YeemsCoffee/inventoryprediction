# Production Business Intelligence Dashboard

## Overview

A production-grade, ML-powered business intelligence dashboard built for analyzing Square point-of-sale data at scale (2,000-3,000 orders/day).

**Technology Stack:**
- **Backend**: PostgreSQL (AWS RDS) with medallion architecture (Bronze/Silver/Gold)
- **Frontend**: Plotly Dash with Bootstrap components
- **ML Integration**: TensorFlow, scikit-learn, XGBoost
- **Performance**: Connection pooling, query caching, materialized views

## Quick Start

### Prerequisites

1. **Database Setup** (one-time):
```bash
# Create database schema
python database/init_database.py

# Load historical data from Square
python scripts/sync_square_to_postgres.py --all
```

2. **Environment Variables** (`.env`):
```bash
DATABASE_URL=postgresql://user:pass@host:5432/inventorybi
SQUARE_ACCESS_TOKEN=your_token_here
SQUARE_ENVIRONMENT=production
```

### Launch Dashboard

```bash
python start_production.py
```

Then open: http://localhost:8050

## Features

### 1. **KPI Cards with Period Comparisons**

Four key metrics with period-over-period change:
- **Total Orders**: Order count with % change from previous period
- **Revenue**: Total sales revenue with trend indicator
- **Average Order Value (AOV)**: Revenue per order
- **Customers**: Unique customer count

**Interpretation:**
- 🟢 Green arrow = metric improved vs previous period
- 🔴 Red arrow = metric declined vs previous period

### 2. **AI-Powered Insights** 🤖

Real-time predictions from ML models:

#### Churn Alerts
```
⚠️ Churn Alert: 23 customers at high risk of churning (>70% probability)
```
- Customers identified with >70% churn probability
- Based on RandomForest model trained on purchase patterns
- Updated weekly from `predictions.customer_churn_scores`

#### Demand Forecasts
```
📈 Top Forecast: Latte - predicted demand: 450 units next week
```
- 7-day ahead forecasts using LSTM + XGBoost models
- Confidence intervals available in database
- Data from `predictions.demand_forecasts`

#### Customer Lifetime Value
```
⭐ Customer Value: Average predicted LTV: $287.50
```
- Predicted total value per customer
- Based on RFM analysis + historical behavior
- From `predictions.customer_ltv_scores`

### 3. **Revenue Trend Analysis**

Dual-axis chart showing:
- **Bars**: Daily revenue ($)
- **Line**: Order count
- **Hover**: Detailed breakdown by date

**Use Cases:**
- Identify high/low revenue days
- Correlate revenue with order volume
- Spot seasonal trends

### 4. **Cohort Analysis** 📊

Retention heatmap showing customer behavior over time:

```
                Oct-24  Nov-24  Dec-24
Oct-24 Cohort   100%    65%     45%
Nov-24 Cohort           100%    72%
Dec-24 Cohort                   100%
```

**How to Read:**
- **Rows**: Customer acquisition month
- **Columns**: Purchase month
- **Values**: % of cohort that purchased in that month
- **Colors**: Green (high retention) → Red (low retention)

**Key Insights:**
- Strong retention: >50% in month 2-3
- Churn patterns: Steep dropoffs
- Seasonal effects: Holiday cohorts

### 5. **Customer Lifetime Value Distribution**

Histogram of customer value buckets:
- **$0-50**: Entry-level customers
- **$50-100**: Regular customers
- **$100-250**: Loyal customers
- **$250-500**: High-value customers
- **$500+**: VIP customers

**Strategy:**
- Focus marketing on $100-250 segment (most convertible)
- Create loyalty program for $250+ segment
- Re-engagement for $0-50 segment

### 6. **Top Products**

Horizontal bar chart of top 10 revenue-generating products.

**Features:**
- Sorted by revenue (highest at top)
- Revenue labels on bars
- Quick identification of best-sellers

**Actions:**
- Stock more inventory for top products
- Bundle low performers with top products
- Adjust pricing based on performance

### 7. **Customer Segmentation**

Pie chart showing customer distribution by behavior:
- **VIP (10+)**: 10+ orders in period
- **Loyal (5-9)**: 5-9 orders
- **Regular (2-4)**: 2-4 orders
- **New (1)**: First-time customers

**Healthy Distribution:**
- ~10-15% VIP
- ~20-25% Loyal
- ~30% Regular
- ~30-40% New

### 8. **Hourly Pattern**

Bar chart of revenue by hour of day (0-23).

**Use Cases:**
- **Staffing**: Schedule more employees during peak hours
- **Inventory**: Restock before rush hours
- **Promotions**: Run happy hour deals during slow periods

**Typical Patterns:**
- Coffee shops: Peak at 7-9am, 12-2pm
- Lunch spots: Peak at 11am-1pm
- Bars: Peak at 5-9pm

### 9. **Weekly Pattern**

Revenue by day of week (Sunday-Saturday).

**Use Cases:**
- **Staffing**: Adjust schedules for busy/slow days
- **Inventory**: Order based on day-of-week demand
- **Marketing**: Target promotions on slow days

**Typical Patterns:**
- Weekends higher for retail/restaurants
- Weekdays higher for business districts

## Filters & Controls

### Date Range Picker

Select custom date ranges for analysis.

**Quick Select Buttons:**
- **7D**: Last 7 days
- **30D**: Last 30 days (default)
- **90D**: Last quarter
- **YTD**: Year-to-date

### Location Filter

- **All Locations**: Aggregate view across all stores
- **Individual Location**: Filter to specific store

**Use Case:** Compare performance across locations.

### Export Button

Click **📥 CSV** to download filtered data:
- Date
- Location
- Product
- Quantity
- Revenue
- Order count

**Use Case:** External analysis in Excel, Tableau, etc.

## Performance Features

### Connection Pooling
- **Technology**: psycopg2 ThreadedConnectionPool
- **Configuration**: 2-10 concurrent connections
- **Benefit**: No memory leaks, stable under load

### Query Caching
- **Technology**: Python @lru_cache decorator
- **Cache Size**: 128 queries
- **Benefit**: Faster repeated queries, lower DB load

### Error Handling
- **Empty States**: Friendly messages when no data available
- **Error States**: Clear error messages with troubleshooting tips
- **Graceful Degradation**: Dashboard works even if some queries fail

## Database Schema

### Layers

1. **Bronze** (`bronze.*`): Raw Square API data
   - `square_orders`
   - `square_line_items`

2. **Silver** (`silver.*`): Cleaned, typed data
   - `customers` (SCD Type 2)
   - `products`
   - `locations`

3. **Gold** (`gold.*`): Star schema for analytics
   - `fact_sales` (partitioned by year)
   - `dim_customer`
   - `dim_product`
   - `dim_location`
   - `dim_date`

4. **Predictions** (`predictions.*`): ML outputs
   - `customer_churn_scores`
   - `demand_forecasts`
   - `customer_ltv_scores`

### Materialized Views

Refreshed after each data load for performance:
- `gold.daily_sales_summary`
- `gold.product_performance`

## ML Models Integration

### How to Generate Predictions

The dashboard displays ML predictions from the database. To populate predictions:

```bash
# 1. Customer churn predictions
python -m src.models.customer_behavior

# 2. Demand forecasting
python -m src.models.advanced_forecaster

# 3. Customer segmentation
python -m src.models.segmentation
```

These scripts write predictions to `predictions.*` tables which the dashboard reads.

### Prediction Freshness

ML insights show data from the last 7 days. To refresh:
1. Re-run ML model scripts (above)
2. Dashboard automatically picks up new predictions
3. No dashboard restart required

## Troubleshooting

### Dashboard won't start

**Error**: `DATABASE_URL not set`
```bash
# Solution: Check .env file
cat .env | grep DATABASE_URL

# Should show:
DATABASE_URL=postgresql://...
```

**Error**: `database "inventorybi" does not exist`
```bash
# Solution: Initialize database
python database/init_database.py
```

### No data showing

**Symptom**: "No Data Available" message

```bash
# Check if data is loaded
python scripts/sync_square_to_postgres.py --all

# Verify data exists
psql $DATABASE_URL -c "SELECT COUNT(*) FROM gold.fact_sales;"
```

### Slow performance

**Symptoms**: Dashboard loads slowly

**Solutions:**
1. Reduce date range (use 30 days instead of 365)
2. Refresh materialized views:
   ```sql
   REFRESH MATERIALIZED VIEW CONCURRENTLY gold.daily_sales_summary;
   REFRESH MATERIALIZED VIEW CONCURRENTLY gold.product_performance;
   ```
3. Check PostgreSQL indexes are created
4. Monitor connection pool usage in logs

### ML insights not showing

**Symptom**: "ML Predictions Not Available Yet"

**Solution**: Run ML models to populate predictions:
```bash
python -m src.models.customer_behavior
python -m src.models.advanced_forecaster
```

### Cohort analysis blank

**Symptom**: "Need multiple months of data"

**Cause**: Cohort analysis requires at least 2 months of historical data.

**Solution**:
- Wait for more data to accumulate, or
- Load more historical data from Square

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Square API (2-3K orders/day)                  │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  sync_square_to_postgres.py                     │
│  (Daily scheduled sync)                         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  AWS RDS PostgreSQL                             │
│  ├── Bronze (raw)                               │
│  ├── Silver (cleaned, partitioned)              │
│  ├── Gold (star schema, materialized views)     │
│  └── Predictions (ML outputs)                   │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Production Dashboard (Dash + Bootstrap)        │
│  ├── Connection Pool (2-10 connections)         │
│  ├── Query Cache (128 queries)                  │
│  ├── Error Handling                             │
│  └── Real-time Updates                          │
└─────────────────────────────────────────────────┘
```

## Roadmap

### Future Enhancements

- [ ] **Real-time updates**: Auto-refresh every 5 minutes
- [ ] **Alerts**: Email/SMS for threshold breaches
- [ ] **Advanced filters**: Product categories, customer segments
- [ ] **Drill-down**: Click charts to explore details
- [ ] **Mobile responsive**: Optimize for phones/tablets
- [ ] **Multi-tenancy**: User authentication & permissions
- [ ] **Custom dashboards**: Save personalized views
- [ ] **Automated reporting**: Scheduled PDF/email reports

### ML Enhancements

- [ ] **Inventory optimization**: Reorder point recommendations
- [ ] **Dynamic pricing**: Price elasticity models
- [ ] **Customer clustering**: Advanced segmentation
- [ ] **Anomaly detection**: Fraud & outlier detection
- [ ] **Recommendation engine**: Product cross-sell/upsell

## Support

### Logs

Check dashboard logs for errors:
```bash
tail -f logs/dashboard_$(date +%Y%m%d).log
```

### Database Queries

Run ad-hoc analysis:
```bash
psql $DATABASE_URL

-- Example: Check data freshness
SELECT MAX(order_timestamp) FROM gold.fact_sales;

-- Example: Count customers
SELECT COUNT(DISTINCT customer_sk) FROM gold.fact_sales;
```

### Performance Monitoring

Monitor connection pool:
```python
# In production_dashboard.py logs
# Look for:
"Database pool initialized (2-10 connections)"
"Query returned 1234 rows"
```

## Best Practices

1. **Data Freshness**: Run Square sync daily or hourly
2. **Backup**: Regular PostgreSQL backups (AWS RDS automated)
3. **Monitoring**: Track dashboard uptime and response times
4. **Security**:
   - Keep `DATABASE_URL` secret
   - Use read-only database user for dashboard
   - Enable SSL for database connections
5. **Scaling**:
   - Increase connection pool for high traffic
   - Add read replicas for heavy analytics
   - Consider Redis for caching layer

---

**Built with:** Python 3.13, PostgreSQL 14, Plotly Dash, TensorFlow, scikit-learn

**Dashboard Version:** 1.0.0 (Production)

**Last Updated:** 2025-11-09
