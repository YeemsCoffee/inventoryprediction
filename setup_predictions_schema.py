"""
Setup predictions schema for ML model outputs.
Creates tables for storing TFT forecasts, churn predictions, and LTV scores.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.database import RDSConnector
from sqlalchemy import text


def setup_predictions_schema():
    """Create predictions schema and tables for ML outputs."""

    print("=" * 70)
    print("🔮 SETTING UP PREDICTIONS SCHEMA")
    print("=" * 70)
    print()

    db = RDSConnector()

    try:
        with db.engine.begin() as conn:
            # Create predictions schema
            print("📊 Creating predictions schema...")
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS predictions"))

            # 1. Demand Forecasts Table (TFT output)
            print("📈 Creating demand_forecasts table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS predictions.demand_forecasts (
                    forecast_id SERIAL PRIMARY KEY,
                    product_name VARCHAR(500) NOT NULL,
                    product_sk INTEGER,
                    forecast_date DATE NOT NULL,
                    forecasted_quantity DECIMAL(10, 2) NOT NULL,
                    confidence_lower DECIMAL(10, 2),
                    confidence_upper DECIMAL(10, 2),
                    model_name VARCHAR(100) DEFAULT 'TFT',
                    prediction_date TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW(),

                    CONSTRAINT unique_product_forecast
                        UNIQUE (product_name, forecast_date, prediction_date)
                )
            """))

            # Index for fast queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_forecasts_date
                ON predictions.demand_forecasts(forecast_date)
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_forecasts_product
                ON predictions.demand_forecasts(product_name)
            """))

            # 2. Customer Churn Scores
            print("👥 Creating customer_churn_scores table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS predictions.customer_churn_scores (
                    churn_id SERIAL PRIMARY KEY,
                    customer_sk INTEGER NOT NULL,
                    customer_id VARCHAR(255),
                    churn_probability DECIMAL(5, 4) NOT NULL,
                    risk_level VARCHAR(20),
                    last_purchase_date DATE,
                    days_since_purchase INTEGER,
                    prediction_date DATE DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP DEFAULT NOW(),

                    CONSTRAINT unique_customer_churn
                        UNIQUE (customer_sk, prediction_date)
                )
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_churn_probability
                ON predictions.customer_churn_scores(churn_probability DESC)
            """))

            # 3. Customer LTV Scores
            print("💰 Creating customer_ltv_scores table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS predictions.customer_ltv_scores (
                    ltv_id SERIAL PRIMARY KEY,
                    customer_sk INTEGER NOT NULL,
                    customer_id VARCHAR(255),
                    predicted_ltv DECIMAL(10, 2) NOT NULL,
                    confidence_interval_lower DECIMAL(10, 2),
                    confidence_interval_upper DECIMAL(10, 2),
                    ltv_segment VARCHAR(50),
                    prediction_date DATE DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP DEFAULT NOW(),

                    CONSTRAINT unique_customer_ltv
                        UNIQUE (customer_sk, prediction_date)
                )
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ltv_value
                ON predictions.customer_ltv_scores(predicted_ltv DESC)
            """))

            # 4. Model Performance Tracking
            print("📊 Creating model_performance table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS predictions.model_performance (
                    performance_id SERIAL PRIMARY KEY,
                    model_name VARCHAR(100) NOT NULL,
                    model_type VARCHAR(50),
                    metric_name VARCHAR(50),
                    metric_value DECIMAL(10, 6),
                    evaluation_date DATE DEFAULT CURRENT_DATE,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))

            # 5. Prediction Metadata
            print("📝 Creating prediction_runs table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS predictions.prediction_runs (
                    run_id SERIAL PRIMARY KEY,
                    model_name VARCHAR(100) NOT NULL,
                    run_timestamp TIMESTAMP DEFAULT NOW(),
                    records_processed INTEGER,
                    predictions_generated INTEGER,
                    execution_time_seconds DECIMAL(10, 2),
                    status VARCHAR(20),
                    error_message TEXT,
                    parameters JSONB
                )
            """))

        print()
        print("✅ Predictions schema created successfully!")
        print()
        print("📊 Created tables:")
        print("   • predictions.demand_forecasts")
        print("   • predictions.customer_churn_scores")
        print("   • predictions.customer_ltv_scores")
        print("   • predictions.model_performance")
        print("   • predictions.prediction_runs")
        print()
        print("=" * 70)

    except Exception as e:
        print(f"❌ Error: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    setup_predictions_schema()
