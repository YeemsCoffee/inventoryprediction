#!/usr/bin/env python3
"""
TFT Forecasting Pipeline using Darts
Trains TFT models and saves predictions to database.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.database import RDSConnector
from src.models.tft_forecaster import TFTForecaster
from sqlalchemy import text


def run_tft_pipeline(
    forecast_days: int = 7,
    min_sales: int = 100,
    max_products: int = 10
):
    """
    Run complete TFT forecasting pipeline.

    Args:
        forecast_days: Days to forecast ahead
        min_sales: Minimum total sales to include product
        max_products: Maximum number of products to forecast
    """
    print("=" * 80)
    print("🚀 TFT FORECASTING PIPELINE (DARTS)")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    db = RDSConnector()

    try:
        # Step 1: Load data from Gold layer
        print("📊 Step 1: Loading data from Gold layer...")
        query = """
        SELECT
            d.date,
            p.product_name as product,
            l.location_name as location,
            l.postal_code,
            f.quantity as amount
        FROM gold.fact_sales f
        JOIN gold.dim_date d ON f.date_key = d.date_key
        JOIN gold.dim_product p ON f.product_sk = p.product_sk
        JOIN gold.dim_location l ON f.location_sk = l.location_sk
        ORDER BY d.date
        """

        with db.engine.connect() as conn:
            data = pd.read_sql(query, conn)

        print(f"✅ Loaded {len(data):,} sales records")
        print(f"📍 Locations: {', '.join(data['location'].unique())}")
        print()

        # Step 2: Select top (product, location) pairs
        print("📦 Step 2: Selecting top (product, location) pairs...")
        product_location_sales = (
            data.groupby(['product', 'location'])['amount']
            .sum()
            .sort_values(ascending=False)
        )
        top_pairs = product_location_sales[product_location_sales >= min_sales].head(max_products)

        print(f"✅ Selected {len(top_pairs)} (product, location) pairs:")
        for i, ((product, location), total) in enumerate(top_pairs.items(), 1):
            print(f"   {i}. {product[:40]:40s} @ {location:15s} (Total: {total:,.0f})")
        print()

        # Step 2.5: Load weather data
        print("🌤️  Step 2.5: Loading weather data...")
        weather_query = """
        SELECT date, zip as postal_code, temp_max, temp_min, precipitation
        FROM gold.weather_daily
        ORDER BY zip, date
        """
        try:
            with db.engine.connect() as conn:
                weather_data = pd.read_sql(weather_query, conn)
            print(f"✅ Loaded {len(weather_data):,} weather records")
            if len(weather_data) == 0:
                print("⚠️  No weather data found. Run: python src/data/weather_data.py")
                weather_data = None
        except Exception as e:
            print(f"⚠️  Could not load weather data: {e}")
            weather_data = None
        print()

        # Step 3: Train models
        print("🤖 Step 3: Training TFT models...")
        forecaster = TFTForecaster(
            data=data,
            location_col='location',
            postal_code_col='postal_code',
            weather_df=weather_data
        )

        all_results = []
        all_predictions = []

        for (product, location) in top_pairs.index:
            try:
                # Train
                result = forecaster.train_tft(
                    product_name=product,
                    location=location,
                    forecast_horizon=forecast_days,
                    input_chunk_length=30,
                    hidden_size=32,
                    num_attention_heads=4,
                    n_epochs=30
                )
                all_results.append(result)

                # Generate predictions
                predictions = forecaster.predict(
                    product_name=product,
                    location=location,
                    n_days=forecast_days
                )
                predictions['model_type'] = 'TFT'
                predictions['trained_at'] = datetime.now()

                all_predictions.append(predictions)

            except Exception as e:
                print(f"⚠️  Skipping {product} @ {location}: {str(e)}")
                continue

        print()

        # Step 4: Save predictions to database
        print("💾 Step 4: Saving predictions to database...")

        # Create predictions schema if not exists
        with db.engine.begin() as conn:
            conn.execute(text("""
                CREATE SCHEMA IF NOT EXISTS predictions
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS predictions.demand_forecasts (
                    id SERIAL PRIMARY KEY,
                    product_name VARCHAR(255),
                    location VARCHAR(100),
                    forecast_date DATE,
                    forecasted_quantity NUMERIC,
                    model_type VARCHAR(50),
                    trained_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Add location column if it doesn't exist (migration for existing tables)
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'predictions'
                        AND table_name = 'demand_forecasts'
                        AND column_name = 'location'
                    ) THEN
                        ALTER TABLE predictions.demand_forecasts
                        ADD COLUMN location VARCHAR(100);
                    END IF;
                END $$;
            """))

            # Add model_type column if it doesn't exist
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'predictions'
                        AND table_name = 'demand_forecasts'
                        AND column_name = 'model_type'
                    ) THEN
                        ALTER TABLE predictions.demand_forecasts
                        ADD COLUMN model_type VARCHAR(50);
                    END IF;
                END $$;
            """))

            # Add trained_at column if it doesn't exist
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'predictions'
                        AND table_name = 'demand_forecasts'
                        AND column_name = 'trained_at'
                    ) THEN
                        ALTER TABLE predictions.demand_forecasts
                        ADD COLUMN trained_at TIMESTAMP;
                    END IF;
                END $$;
            """))

            # Clear all old predictions (we're regenerating them)
            conn.execute(text("""
                TRUNCATE TABLE predictions.demand_forecasts
            """))

        # Save new predictions
        if all_predictions:
            predictions_df = pd.concat(all_predictions, ignore_index=True)
            predictions_df.to_sql(
                'demand_forecasts',
                db.engine,
                schema='predictions',
                if_exists='append',
                index=False
            )

            print(f"✅ Saved {len(predictions_df):,} predictions to database")
        else:
            print("⚠️  No predictions to save")

        print()

        # Step 5: Summary
        print("=" * 80)
        print("✅ PIPELINE COMPLETE!")
        print("=" * 80)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("📊 Summary:")
        print(f"   (Product, Location) pairs trained: {len(all_results)}")
        print(f"   Predictions generated: {len(all_predictions) * forecast_days if all_predictions else 0}")
        print(f"   Forecast horizon: {forecast_days} days")
        print()

        if all_results:
            print("📈 Model Performance:")
            for result in all_results:
                print(f"   {result['product'][:40]:40s} @ {result['location']:15s} | MAE: {result['mae']:8.2f} | RMSE: {result['rmse']:8.2f}")

        print()
        print("=" * 80)

    except Exception as e:
        print(f"❌ Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run TFT forecasting pipeline')
    parser.add_argument('--days', type=int, default=7, help='Days to forecast')
    parser.add_argument('--min-sales', type=int, default=100, help='Minimum sales to include product')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum products to forecast')

    args = parser.parse_args()

    run_tft_pipeline(
        forecast_days=args.days,
        min_sales=args.min_sales,
        max_products=args.max_products
    )
