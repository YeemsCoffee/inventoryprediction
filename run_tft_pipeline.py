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
            f.quantity as amount
        FROM gold.fact_sales f
        JOIN gold.dim_date d ON f.date_key = d.date_key
        JOIN gold.dim_product p ON f.product_sk = p.product_sk
        ORDER BY d.date
        """

        with db.engine.connect() as conn:
            data = pd.read_sql(query, conn)

        print(f"✅ Loaded {len(data):,} sales records")
        print()

        # Step 2: Select top products
        print("📦 Step 2: Selecting top products...")
        product_sales = data.groupby('product')['amount'].sum().sort_values(ascending=False)
        top_products = product_sales[product_sales >= min_sales].head(max_products)

        print(f"✅ Selected {len(top_products)} products:")
        for i, (product, total) in enumerate(top_products.items(), 1):
            print(f"   {i}. {product[:50]:50s} (Total: {total:,.0f})")
        print()

        # Step 2.5: Load weather data
        print("🌤️  Step 2.5: Loading weather data...")
        weather_query = """
        SELECT date, location, temp_max, temp_min, precipitation
        FROM gold.weather_daily
        ORDER BY location, date
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
        forecaster = TFTForecaster(data, weather_data=weather_data)

        all_results = []
        all_predictions = []

        for product in top_products.index:
            try:
                # Train
                result = forecaster.train_tft(
                    product_name=product,
                    forecast_horizon=forecast_days,
                    input_chunk_length=30,
                    hidden_size=32,
                    num_attention_heads=4,
                    n_epochs=30
                )
                all_results.append(result)

                # Generate predictions
                predictions = forecaster.predict(product, n_days=forecast_days)
                predictions['model_type'] = 'TFT'
                predictions['trained_at'] = datetime.now()

                all_predictions.append(predictions)

            except Exception as e:
                print(f"⚠️  Skipping {product}: {str(e)}")
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
                    forecast_date DATE,
                    forecasted_quantity NUMERIC,
                    model_type VARCHAR(50),
                    trained_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Clear old predictions
            conn.execute(text("""
                DELETE FROM predictions.demand_forecasts
                WHERE forecast_date >= CURRENT_DATE
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
        print(f"   Products trained: {len(all_results)}")
        print(f"   Predictions generated: {len(all_predictions) * forecast_days if all_predictions else 0}")
        print(f"   Forecast horizon: {forecast_days} days")
        print()

        if all_results:
            print("📈 Model Performance:")
            for result in all_results:
                print(f"   {result['product'][:50]:50s} | MAE: {result['mae']:8.2f} | RMSE: {result['rmse']:8.2f}")

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
