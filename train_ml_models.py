#!/usr/bin/env python3
"""
Train ML models on PostgreSQL data and save predictions.

This script:
1. Pulls historical sales data from PostgreSQL
2. Trains forecasting models (demand, revenue, customer trends)
3. Saves predictions to database for dashboard display
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

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.advanced_forecaster import AdvancedForecaster
from src.models.customer_behavior import CustomerBehaviorAnalyzer
from src.models.segmentation import CustomerSegmentation

print("=" * 80)
print("🤖 ML MODEL TRAINING PIPELINE")
print("=" * 80)

# Get database connection
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("❌ ERROR: DATABASE_URL not found in .env file")
    sys.exit(1)

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

# Load daily sales aggregates (using ALL available data)
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

# Load product-level data (using ALL available data)
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

# Load customer data
customer_query = """
    SELECT
        dc.customer_id,
        dc.customer_sk,
        dc.first_order_date,
        dc.lifetime_value,
        dc.customer_segment,
        COUNT(DISTINCT fs.order_id) as order_count,
        MAX(fs.order_timestamp) as last_order_date,
        AVG(fs.net_amount) as avg_order_value
    FROM gold.dim_customer dc
    LEFT JOIN gold.fact_sales fs ON dc.customer_sk = fs.customer_sk AND dc.is_current = TRUE
    WHERE dc.is_current = TRUE
    GROUP BY dc.customer_id, dc.customer_sk, dc.first_order_date, dc.lifetime_value, dc.customer_segment
"""

df_customers = pd.read_sql(customer_query, engine)
print(f"✅ Loaded {len(df_customers)} customer records")

# ============================================================================
# 2. TRAIN DEMAND FORECASTING MODEL
# ============================================================================

print("\n" + "=" * 80)
print("🔮 Step 2: Training demand forecasting model...")
print("=" * 80)

try:
    forecaster = AdvancedForecaster(df_sales)

    # Train model on revenue
    print("   Training LSTM model on revenue data...")
    result = forecaster.train_lstm_forecast(
        date_column='date',
        value_column='revenue',
        lookback=30,
        epochs=50,
        frequency='D'
    )

    if result:
        print("   ✅ LSTM model trained successfully")

        # Generate 30-day forecast
        print("   Generating 30-day forecast...")
        forecast = forecaster.forecast_next_n_days(n_days=30)

        if forecast is not None:
            print(f"   ✅ Generated forecast for next 30 days")
            print(f"      Predicted total revenue: ${forecast['predicted'].sum():,.2f}")

            # Save forecasts to database
            print("   Saving forecasts to database...")

            # Create predictions table if not exists
            cursor.execute("""
                CREATE SCHEMA IF NOT EXISTS predictions;

                CREATE TABLE IF NOT EXISTS predictions.demand_forecasts (
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

            # Insert revenue forecasts
            for _, row in forecast.iterrows():
                cursor.execute("""
                    INSERT INTO predictions.demand_forecasts
                    (forecast_date, product_name, forecasted_revenue, model_type)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (forecast_date, product_name) DO UPDATE
                    SET forecasted_revenue = EXCLUDED.forecasted_revenue,
                        created_at = NOW()
                """, (row['date'], 'Overall', row['predicted'], 'LSTM'))

            conn.commit()
            print("   ✅ Forecasts saved to predictions.demand_forecasts")
    else:
        print("   ⚠️  LSTM training failed (TensorFlow may not be installed)")
        print("   Install with: pip install tensorflow")

except Exception as e:
    print(f"   ⚠️  Error in forecasting: {e}")
    print("   Continuing with other models...")

# ============================================================================
# 3. TRAIN CUSTOMER SEGMENTATION
# ============================================================================

print("\n" + "=" * 80)
print("👥 Step 3: Training customer segmentation model...")
print("=" * 80)

try:
    segmentation = CustomerSegmentation(df_customers)

    # Perform RFM segmentation
    print("   Calculating RFM scores...")
    rfm_df = segmentation.rfm_segmentation(
        customer_id='customer_id',
        recency_col='last_order_date',
        frequency_col='order_count',
        monetary_col='lifetime_value'
    )

    print(f"   ✅ Segmented {len(rfm_df)} customers")

    # Show segment distribution
    print("\n   Customer Segments:")
    segment_dist = rfm_df['segment'].value_counts()
    for segment, count in segment_dist.items():
        print(f"      {segment}: {count} customers ({count/len(rfm_df)*100:.1f}%)")

    # Update customer segments in database
    print("\n   Updating customer segments in database...")
    for _, row in rfm_df.iterrows():
        cursor.execute("""
            UPDATE gold.dim_customer
            SET customer_segment = %s
            WHERE customer_id = %s AND is_current = TRUE
        """, (row['segment'], row['customer_id']))

    conn.commit()
    print("   ✅ Customer segments updated in gold.dim_customer")

except Exception as e:
    print(f"   ⚠️  Error in customer segmentation: {e}")

# ============================================================================
# 4. PRODUCT DEMAND FORECASTING
# ============================================================================

print("\n" + "=" * 80)
print("📦 Step 4: Training product-level demand forecasts...")
print("=" * 80)

# Get top 10 products by revenue
top_products = df_products.groupby('product_name')['revenue'].sum().nlargest(10)
print(f"   Forecasting demand for top {len(top_products)} products")

for product in top_products.index:
    try:
        product_data = df_products[df_products['product_name'] == product].copy()
        product_data = product_data.set_index('date')['quantity_sold'].resample('D').sum().fillna(0)

        if len(product_data) >= 30:  # Need at least 30 days
            # Simple moving average forecast (you can upgrade to LSTM later)
            forecast_days = 7
            ma_window = 7

            # Calculate moving average
            ma = product_data.rolling(window=ma_window).mean()
            last_ma = ma.iloc[-1]

            # Generate forecast dates
            last_date = product_data.index[-1]
            forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=forecast_days)

            # Save to database
            for forecast_date in forecast_dates:
                cursor.execute("""
                    INSERT INTO predictions.demand_forecasts
                    (forecast_date, product_name, forecasted_quantity, model_type)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (forecast_date, product_name) DO UPDATE
                    SET forecasted_quantity = EXCLUDED.forecasted_quantity,
                        created_at = NOW()
                """, (forecast_date.date(), product, float(last_ma), 'Moving Average'))

            print(f"   ✅ {product}: forecast ~{last_ma:.1f} units/day")

    except Exception as e:
        print(f"   ⚠️  Error forecasting {product}: {e}")

conn.commit()

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("✅ ML MODEL TRAINING COMPLETE!")
print("=" * 80)

# Get forecast summary
cursor.execute("""
    SELECT
        COUNT(DISTINCT forecast_date) as forecast_days,
        COUNT(DISTINCT product_name) as products,
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
print("   1. Refresh your dashboard to see ML insights")
print("   2. Check predictions.demand_forecasts table for raw forecasts")
print("   3. Run this script daily/weekly to keep forecasts updated")
print("   4. Upgrade to LSTM for better accuracy (install tensorflow)")

print("\n🔧 To run this automatically:")
print("   Add to cron: 0 2 * * * cd /path/to/project && python train_ml_models.py")

cursor.close()
conn.close()
engine.dispose()

print("\n" + "=" * 80)
