#!/usr/bin/env python3
"""
Train LSTM deep learning model on PostgreSQL data and save predictions.

Uses TensorFlow/Keras LSTM neural network for revenue forecasting
and RFM analysis for customer segmentation.
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
# 3. LSTM FORECASTING (DEEP LEARNING)
# ============================================================================

print("\n" + "=" * 80)
print("🧠 Step 3: Training LSTM model (deep learning)...")
print("=" * 80)

try:
    from tensorflow import keras
    from tensorflow.keras import layers
    from sklearn.preprocessing import MinMaxScaler

    print("   TensorFlow detected! Training LSTM model...")

    # Prepare data for LSTM
    if len(df_sales) >= 60:  # Need at least 60 days for LSTM
        # Sort and prepare revenue series
        df_sales_sorted = df_sales.sort_values('date')
        revenue_series = df_sales_sorted['revenue'].values.reshape(-1, 1)

        # Scale data
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(revenue_series)

        # Create sequences (use 30 days to predict next day)
        lookback = 30
        X, y = [], []
        for i in range(lookback, len(scaled_data)):
            X.append(scaled_data[i-lookback:i, 0])
            y.append(scaled_data[i, 0])

        X, y = np.array(X), np.array(y)
        X = X.reshape((X.shape[0], X.shape[1], 1))

        # Split train/test
        split = int(0.8 * len(X))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        print(f"   Training on {len(X_train)} samples...")

        # Build LSTM model
        model = keras.Sequential([
            layers.LSTM(50, return_sequences=True, input_shape=(lookback, 1)),
            layers.Dropout(0.2),
            layers.LSTM(50, return_sequences=False),
            layers.Dropout(0.2),
            layers.Dense(25),
            layers.Dense(1)
        ])

        model.compile(optimizer='adam', loss='mse')

        # Train model
        history = model.fit(
            X_train, y_train,
            epochs=20,
            batch_size=32,
            validation_split=0.1,
            verbose=0
        )

        print(f"   ✅ LSTM trained! Final loss: {history.history['loss'][-1]:.4f}")

        # Generate predictions
        print("   Generating LSTM forecasts...")

        # Start from last sequence
        last_sequence = scaled_data[-lookback:]
        predictions = []

        # Predict next 30 days
        for _ in range(30):
            # Reshape for prediction
            seq = last_sequence.reshape((1, lookback, 1))
            pred = model.predict(seq, verbose=0)
            predictions.append(pred[0, 0])

            # Update sequence
            last_sequence = np.append(last_sequence[1:], pred)

        # Inverse transform predictions
        predictions = np.array(predictions).reshape(-1, 1)
        forecasted_revenue = scaler.inverse_transform(predictions)

        # Save LSTM forecasts
        today = datetime.now().date()
        forecast_dates = pd.date_range(start=today, periods=30)

        for i, forecast_date in enumerate(forecast_dates):
            cursor.execute("""
                INSERT INTO predictions.demand_forecasts
                (forecast_date, product_name, forecasted_revenue, model_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (forecast_date, product_name) DO UPDATE
                SET forecasted_revenue = EXCLUDED.forecasted_revenue,
                    model_type = EXCLUDED.model_type,
                    created_at = NOW()
            """, (forecast_date.date(), 'Overall_LSTM', float(forecasted_revenue[i][0]), 'LSTM'))

        conn.commit()
        print(f"   ✅ LSTM forecasts saved!")
        print(f"      Average forecast: ${forecasted_revenue.mean():,.2f}/day")

    else:
        print(f"   ❌ ERROR: Need at least 60 days of data for LSTM (have {len(df_sales)} days)")
        print(f"   Please import more historical data to train the model.")
        sys.exit(1)

except ImportError:
    print("   ❌ ERROR: TensorFlow not installed.")
    print("      Install with: pip install tensorflow")
    print("      Or: pip install tensorflow scikit-learn")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ LSTM training error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

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

    # Monetary score based on revenue percentiles
    # Use percentiles to ensure unique bins
    q25 = df_customers['monetary'].quantile(0.25)
    q50 = df_customers['monetary'].quantile(0.50)
    q75 = df_customers['monetary'].quantile(0.75)
    max_val = df_customers['monetary'].max()

    # Create unique bins
    bins = [0, q25, q50, q75, max_val + 1]
    # Remove duplicates while maintaining order
    unique_bins = []
    for b in bins:
        if not unique_bins or b > unique_bins[-1]:
            unique_bins.append(b)

    # Create labels based on number of unique bins
    labels = list(range(1, len(unique_bins)))

    if len(labels) >= 1:
        df_customers['m_score'] = pd.cut(df_customers['monetary'],
                                          bins=unique_bins,
                                          labels=labels,
                                          include_lowest=True)
    else:
        df_customers['m_score'] = 2  # Default middle score if all same

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
print("   1. Refresh your dashboard to see LSTM forecasts")
print("   2. Run this script weekly to keep predictions updated")
print("   3. Monitor model performance and retrain as needed")

print("\n" + "=" * 80)

cursor.close()
conn.close()
engine.dispose()
