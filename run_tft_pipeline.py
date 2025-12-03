"""
TFT Forecasting Pipeline - Generate demand forecasts and save to RDS.
Runs Temporal Fusion Transformer on Gold layer data and stores predictions.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.database import RDSConnector
from src.models.tft_forecaster import TFTForecaster
from sqlalchemy import text


def run_tft_pipeline(forecast_days: int = 30,
                     max_epochs: int = 30,
                     batch_size: int = 128,
                     save_to_db: bool = True):
    """
    Run complete TFT forecasting pipeline.

    Args:
        forecast_days: Number of days to forecast
        max_epochs: Maximum training epochs
        batch_size: Training batch size
        save_to_db: Save results to predictions schema

    Returns:
        DataFrame with forecasts
    """

    print("=" * 70)
    print("🚀 TFT DEMAND FORECASTING PIPELINE")
    print("=" * 70)
    print(f"Forecast horizon: {forecast_days} days")
    print(f"Training epochs: {max_epochs}")
    print()

    start_time = time.time()
    db = RDSConnector()

    try:
        # Step 1: Load data from Gold layer
        print("📊 Step 1: Loading data from Gold layer...")
        print("-" * 70)

        query = """
            SELECT
                fs.order_timestamp as date,
                dp.product_name as product,
                fs.quantity as amount,
                dc.customer_id
            FROM gold.fact_sales fs
            JOIN gold.dim_product dp ON fs.product_sk = dp.product_sk
            LEFT JOIN gold.dim_customer dc ON fs.customer_sk = dc.customer_sk
            WHERE fs.order_timestamp >= '2022-01-01'
            ORDER BY fs.order_timestamp
        """

        with db.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)

        print(f"✅ Loaded {len(df):,} transactions from Gold layer")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"   Products: {df['product'].nunique():,}")
        print()

        # Step 2: Initialize and train TFT
        print("🤖 Step 2: Training Temporal Fusion Transformer...")
        print("-" * 70)

        tft = TFTForecaster(df)

        training_results = tft.train_tft(
            max_epochs=max_epochs,
            batch_size=batch_size
        )

        print()

        # Step 3: Generate forecasts
        print("🔮 Step 3: Generating forecasts...")
        print("-" * 70)

        forecasts_df = tft.forecast(periods=forecast_days)

        print()

        # Step 4: Get variable importance
        print("📊 Step 4: Analyzing variable importance...")
        print("-" * 70)

        importance_df = tft.get_variable_importance()

        print()

        # Step 5: Save to database (if requested)
        if save_to_db:
            print("💾 Step 5: Saving forecasts to RDS...")
            print("-" * 70)

            save_forecasts_to_db(db, forecasts_df, forecast_days)

            # Track pipeline run
            execution_time = time.time() - start_time
            track_pipeline_run(db, forecasts_df, execution_time, max_epochs, batch_size)

        # Summary
        elapsed = time.time() - start_time
        print()
        print("=" * 70)
        print("✅ TFT PIPELINE COMPLETE!")
        print("=" * 70)
        print(f"⏱️  Execution time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"📈 Products forecasted: {len(forecasts_df):,}")
        print(f"📅 Forecast horizon: {forecast_days} days")

        if save_to_db:
            print(f"💾 Forecasts saved to: predictions.demand_forecasts")
            print()
            print("🎯 Your dashboard will now show TFT predictions!")
            print("   View at: http://localhost:8050")

        print()
        print("=" * 70)

        return forecasts_df

    except Exception as e:
        print(f"❌ Pipeline failed: {str(e)}")

        # Track failed run
        if save_to_db:
            track_pipeline_run(db, None, time.time() - start_time,
                             max_epochs, batch_size,
                             status='failed', error=str(e))

        raise

    finally:
        db.close()


def save_forecasts_to_db(db: RDSConnector, forecasts_df: pd.DataFrame, forecast_days: int):
    """
    Save TFT forecasts to predictions.demand_forecasts table.

    Args:
        db: Database connector
        forecasts_df: DataFrame with forecasts from TFT
        forecast_days: Number of forecast days
    """

    today = datetime.now().date()
    prediction_timestamp = datetime.now()

    records_inserted = 0

    with db.engine.begin() as conn:
        for _, row in forecasts_df.iterrows():
            product_name = row['product']
            forecast_values = row['forecast']

            # Insert forecast for each day
            for day_offset, forecasted_qty in enumerate(forecast_values[:forecast_days]):
                forecast_date = today + timedelta(days=day_offset + 1)

                # Calculate confidence intervals (simplified - 80% bounds)
                confidence_lower = forecasted_qty * 0.8
                confidence_upper = forecasted_qty * 1.2

                insert_sql = text("""
                    INSERT INTO predictions.demand_forecasts (
                        product_name, forecast_date, forecasted_quantity,
                        confidence_lower, confidence_upper, model_name, prediction_date
                    )
                    VALUES (
                        :product_name, :forecast_date, :forecasted_quantity,
                        :confidence_lower, :confidence_upper, :model_name, :prediction_date
                    )
                    ON CONFLICT (product_name, forecast_date, prediction_date)
                    DO UPDATE SET
                        forecasted_quantity = EXCLUDED.forecasted_quantity,
                        confidence_lower = EXCLUDED.confidence_lower,
                        confidence_upper = EXCLUDED.confidence_upper
                """)

                conn.execute(insert_sql, {
                    'product_name': product_name,
                    'forecast_date': forecast_date,
                    'forecasted_quantity': float(forecasted_qty),
                    'confidence_lower': float(confidence_lower),
                    'confidence_upper': float(confidence_upper),
                    'model_name': 'Temporal Fusion Transformer',
                    'prediction_date': prediction_timestamp
                })

                records_inserted += 1

            if (_ + 1) % 100 == 0:
                print(f"  Progress: {_ + 1:,} / {len(forecasts_df):,} products")

    print(f"✅ Saved {records_inserted:,} forecast records to database")


def track_pipeline_run(db: RDSConnector, forecasts_df, execution_time: float,
                       max_epochs: int, batch_size: int,
                       status: str = 'success', error: str = None):
    """
    Track pipeline execution in prediction_runs table.

    Args:
        db: Database connector
        forecasts_df: Forecasts dataframe (None if failed)
        execution_time: Execution time in seconds
        max_epochs: Training epochs used
        batch_size: Batch size used
        status: 'success' or 'failed'
        error: Error message if failed
    """

    try:
        with db.engine.begin() as conn:
            records_processed = len(forecasts_df) if forecasts_df is not None else 0
            predictions_generated = records_processed * 30  # 30 days per product

            insert_sql = text("""
                INSERT INTO predictions.prediction_runs (
                    model_name, records_processed, predictions_generated,
                    execution_time_seconds, status, error_message, parameters
                )
                VALUES (
                    :model_name, :records_processed, :predictions_generated,
                    :execution_time, :status, :error_message,
                    :parameters::jsonb
                )
            """)

            import json
            params_json = json.dumps({
                'max_epochs': max_epochs,
                'batch_size': batch_size,
                'forecast_horizon': 30
            })

            conn.execute(insert_sql, {
                'model_name': 'Temporal Fusion Transformer',
                'records_processed': records_processed,
                'predictions_generated': predictions_generated,
                'execution_time': execution_time,
                'status': status,
                'error_message': error,
                'parameters': params_json
            })

    except Exception as e:
        print(f"⚠️  Could not track pipeline run: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run TFT forecasting pipeline')
    parser.add_argument('--forecast-days', type=int, default=30,
                       help='Number of days to forecast (default: 30)')
    parser.add_argument('--epochs', type=int, default=30,
                       help='Training epochs (default: 30)')
    parser.add_argument('--batch-size', type=int, default=128,
                       help='Batch size (default: 128)')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save to database (test mode)')

    args = parser.parse_args()

    run_tft_pipeline(
        forecast_days=args.forecast_days,
        max_epochs=args.epochs,
        batch_size=args.batch_size,
        save_to_db=not args.no_save
    )
