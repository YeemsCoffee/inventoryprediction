#!/usr/bin/env python3
"""
Train ML models on PostgreSQL data and save predictions.

Simplified version that does basic forecasting and saves to database.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2
from sqlalchemy import create_engine

# Load environment
load_dotenv()

database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("❌ ERROR: DATABASE_URL not found in .env file")
    sys.exit(1)

print("=" * 80)
print("🤖 ML MODEL TRAINING PIPELINE")
print("=" * 80)

engine = create_engine(database_url)
conn = psycopg2.connect(database_url)
cursor = conn.cursor()

print("\n✅ Connected to database")

# ============================================================================
# 1. LOAD HISTORICAL DATA
# ============================================================================

print("\n" + "=" * 80)
print("📊 Step 1: Loading historical sales data...")
print("=" * 80)

sales_query = """
    SELECT
        DATE(order_timestamp) as date,
        COUNT(DISTINCT order_id) as orders,
        SUM(net_amount) as revenue,
        SUM(quantity) as items_sold,
        COUNT(DISTINCT customer_sk) as unique_customers
    FROM gold.fact_sales
    GROUP BY DATE(order_timestamp)
    ORDER BY date
"""

df_sales = pd.read_sql(sales_query, engine)
print(f"✅ Loaded {len(df_sales)} days of sales data")
print(f"   Date range: {df_sales['date'].min()} to {df_sales['date'].max()}")
print(f"   Total revenue: ${df_sales['revenue'].sum():,.2f}")

# Load product-level data
product_query = """
    SELECT
        DATE(fs.order_timestamp) as date,
        dp.product_name,
        SUM(fs.quantity) as quantity_sold,
        SUM(fs.net_amount) as revenue
    FROM gold.fact_sales fs
    JOIN gold.dim_product dp ON fs.product_sk = dp.product_sk
    GROUP BY DATE(fs.order_timestamp), dp.product_name
    ORDER BY date, dp.product_name
"""

df_products = pd.read_sql(product_query, engine)
print(f"✅ Loaded product-level data: {df_products['product_name'].nunique()} unique products")

# ============================================================================
# 2. CREATE PREDICTIONS TABLE
# ============================================================================

print("\n" + "=" * 80)
print("🗄️  Step 2: Setting up predictions table...")
print("=" * 80)

cursor.execute("""
    CREATE SCHEMA IF NOT EXISTS predictions;

    DROP TABLE IF EXISTS predictions.demand_forecasts;

    CREATE TABLE predictions.demand_forecasts (
        forecast_id SERIAL PRIMARY KEY,
        forecast_date DATE NOT NULL,
        product_name VARCHAR(500),
        forecasted_quantity NUMERIC(10,2),
        forecasted_revenue NUMERIC(12,2),
        confidence_lower NUMERIC(12,2),
        confidence_upper NUMERIC(12,2),
        model_type VARCHAR(50),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(forecast_date, product_name)
    );
""")
conn.commit()
print("✅ Predictions table created")

# ============================================================================
# 3. SIMPLE MOVING AVERAGE FORECASTING
# ============================================================================

print("\n" + "=" * 80)
print("📈 Step 3: Generating forecasts using Moving Average...")
print("=" * 80)

# Overall revenue forecast
print("   Forecasting overall revenue...")
if len(df_sales) >= 7:
    # Use 7-day moving average
    df_sales_sorted = df_sales.sort_values('date')
    recent_avg = df_sales_sorted.tail(7)['revenue'].mean()

    # Generate 30-day forecast
    last_date = df_sales_sorted['date'].max()
    forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=30)

    for forecast_date in forecast_dates:
        cursor.execute("""
            INSERT INTO predictions.demand_forecasts
            (forecast_date, product_name, forecasted_revenue, model_type)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (forecast_date, product_name) DO UPDATE
            SET forecasted_revenue = EXCLUDED.forecasted_revenue,
                created_at = NOW()
        """, (forecast_date.date(), 'Overall', float(recent_avg), 'Moving Average'))

    conn.commit()
    print(f"   ✅ Overall forecast: ~${recent_avg:,.2f}/day for next 30 days")
else:
    print("   ⚠️  Not enough data for overall forecast (need at least 7 days)")

# Product-level forecasts
print("\n   Forecasting top products...")
top_products = df_products.groupby('product_name')['revenue'].sum().nlargest(10)
forecast_count = 0

for product in top_products.index:
    try:
        product_data = df_products[df_products['product_name'] == product].copy()

        # Aggregate by date and sort
        daily_data = product_data.groupby('date').agg({
            'quantity_sold': 'sum',
            'revenue': 'sum'
        }).sort_index()

        if len(daily_data) >= 7:
            # 7-day moving average
            recent_quantity = daily_data.tail(7)['quantity_sold'].mean()
            recent_revenue = daily_data.tail(7)['revenue'].mean()

            # Generate 7-day forecast
            last_date = daily_data.index[-1]
            forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=7)

            for forecast_date in forecast_dates:
                cursor.execute("""
                    INSERT INTO predictions.demand_forecasts
                    (forecast_date, product_name, forecasted_quantity, forecasted_revenue, model_type)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (forecast_date, product_name) DO UPDATE
                    SET forecasted_quantity = EXCLUDED.forecasted_quantity,
                        forecasted_revenue = EXCLUDED.forecasted_revenue,
                        created_at = NOW()
                """, (forecast_date.date(), product, float(recent_quantity), float(recent_revenue), 'Moving Average'))

            forecast_count += 1
            print(f"   ✅ {product}: ~{recent_quantity:.1f} units/day, ${recent_revenue:.2f}/day")

    except Exception as e:
        print(f"   ⚠️  Error forecasting {product}: {e}")

conn.commit()
print(f"\n   ✅ Successfully forecasted {forecast_count} products")

# ============================================================================
# 4. CUSTOMER SEGMENTATION (SIMPLE RFM)
# ============================================================================

print("\n" + "=" * 80)
print("👥 Step 4: Performing customer segmentation...")
print("=" * 80)

customer_query = """
    SELECT
        dc.customer_id,
        dc.customer_sk,
        COUNT(DISTINCT fs.order_id) as frequency,
        COALESCE(SUM(fs.net_amount), 0) as monetary,
        EXTRACT(DAY FROM (CURRENT_DATE - MAX(fs.order_timestamp))) as recency_days
    FROM gold.dim_customer dc
    LEFT JOIN gold.fact_sales fs ON dc.customer_sk = fs.customer_sk
    WHERE dc.is_current = TRUE
    GROUP BY dc.customer_id, dc.customer_sk
    HAVING COUNT(DISTINCT fs.order_id) > 0
"""

df_customers = pd.read_sql(customer_query, engine)
print(f"   Analyzing {len(df_customers)} customers...")

if len(df_customers) > 0:
    # Simple RFM scoring using percentiles (more robust than qcut)
    df_customers['r_score'] = pd.cut(df_customers['recency_days'],
                                      bins=[-1, 7, 30, 90, float('inf')],
                                      labels=[4, 3, 2, 1])

    # Frequency score based on order count
    df_customers['f_score'] = pd.cut(df_customers['frequency'],
                                      bins=[0, 1, 3, 6, float('inf')],
                                      labels=[1, 2, 3, 4])

    # Monetary score based on revenue
    median_revenue = df_customers['monetary'].median()
    mean_revenue = df_customers['monetary'].mean()
    df_customers['m_score'] = pd.cut(df_customers['monetary'],
                                      bins=[0, median_revenue*0.5, median_revenue, mean_revenue, float('inf')],
                                      labels=[1, 2, 3, 4])

    # Assign segments based on RFM scores
    def assign_segment(row):
        try:
            r = int(row['r_score']) if pd.notna(row['r_score']) else 2
            f = int(row['f_score']) if pd.notna(row['f_score']) else 2
            m = int(row['m_score']) if pd.notna(row['m_score']) else 2
            avg_score = (r + f + m) / 3

            if avg_score >= 3.5:
                return 'High Value'
            elif avg_score >= 3.0:
                return 'Loyal'
            elif avg_score >= 2.0:
                return 'Potential'
            elif r <= 2:
                return 'At Risk'
            else:
                return 'New'
        except:
            return 'Unknown'

    df_customers['segment'] = df_customers.apply(assign_segment, axis=1)

    # Show distribution
    print("\n   Customer Segments:")
    segment_dist = df_customers['segment'].value_counts()
    for segment, count in segment_dist.items():
        pct = count / len(df_customers) * 100
        print(f"      {segment}: {count} customers ({pct:.1f}%)")

    # Update database
    print("\n   Updating customer segments in database...")
    update_count = 0
    for _, row in df_customers.iterrows():
        cursor.execute("""
            UPDATE gold.dim_customer
            SET customer_segment = %s
            WHERE customer_id = %s AND is_current = TRUE
        """, (row['segment'], row['customer_id']))
        update_count += 1

    conn.commit()
    print(f"   ✅ Updated {update_count} customer segments")
else:
    print("   ⚠️  No customer data found")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("✅ ML MODEL TRAINING COMPLETE!")
print("=" * 80)

cursor.execute("""
    SELECT
        COUNT(DISTINCT forecast_date) as forecast_days,
        COUNT(DISTINCT COALESCE(product_name, 'Overall')) as products,
        SUM(forecasted_revenue) as total_forecasted_revenue
    FROM predictions.demand_forecasts
    WHERE forecast_date >= CURRENT_DATE
""")

summary = cursor.fetchone()
if summary:
    print(f"\n📊 Forecast Summary:")
    print(f"   Forecast days: {summary[0]}")
    print(f"   Products forecasted: {summary[1]}")
    if summary[2]:
        print(f"   Total forecasted revenue: ${summary[2]:,.2f}")

print("\n💡 Next steps:")
print("   1. Refresh your dashboard to see forecasts")
print("   2. Run this script weekly to keep predictions updated")
print("   3. Optional: Install tensorflow for LSTM models (pip install tensorflow)")

print("\n" + "=" * 80)

cursor.close()
conn.close()
engine.dispose()
