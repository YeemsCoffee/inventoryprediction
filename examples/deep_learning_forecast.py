"""
Example: Advanced forecasting with Deep Learning (LSTM) and XGBoost.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import CustomerTrendApp
from src.models.advanced_forecaster import AdvancedForecaster


def main():
    """Demonstrate advanced ML forecasting."""

    print("=" * 70)
    print("DEEP LEARNING & ADVANCED ML FORECASTING")
    print("=" * 70)

    # Create sample data
    print("\n📊 Creating sample data...")
    app = CustomerTrendApp()
    app.create_sample_data(n_customers=200, n_transactions=10000,
                          start_date='2022-01-01', end_date='2024-12-31')

    data = app.processed_data

    print(f"✅ Created {len(data)} transactions")

    # Initialize advanced forecaster
    forecaster = AdvancedForecaster(data)

    # Train LSTM model
    print("\n📋 Training LSTM (Deep Learning) Model...")
    print("-" * 70)

    lstm_result = forecaster.train_lstm_forecast(
        date_column='date',
        value_column='amount',
        lookback=30,
        epochs=20,
        frequency='D'
    )

    if 'error' not in lstm_result:
        print(f"✅ LSTM Model trained successfully!")
        print(f"   Training Loss: {lstm_result['train_loss']:.4f}")
        print(f"   Validation Loss: {lstm_result['val_loss']:.4f}")

        # Generate forecast
        print("\n🔮 Generating 30-day forecast with LSTM...")
        forecast = forecaster.forecast_lstm(periods=30, lookback=30)

        if not forecast.empty and 'error' not in forecast.columns:
            print(f"✅ Forecast generated!")
            print(f"\nFirst 5 days of forecast:")
            print(forecast.head())
            print(f"\nAverage predicted demand: {forecast['yhat'].mean():.2f} items/day")

    # Train XGBoost model
    print("\n📋 Training XGBoost Model...")
    print("-" * 70)

    xgb_result = forecaster.train_xgboost_forecast(
        date_column='date',
        value_column='amount',
        frequency='D'
    )

    if 'error' not in xgb_result:
        print(f"✅ XGBoost Model trained successfully!")
        print(f"   Training R²: {xgb_result['train_score']:.4f}")
        print(f"   Test R²: {xgb_result['test_score']:.4f}")

        print(f"\nTop 5 Important Features:")
        importance = sorted(xgb_result['feature_importance'].items(),
                          key=lambda x: x[1], reverse=True)[:5]
        for feature, imp in importance:
            print(f"   {feature}: {imp:.4f}")

    print("\n" + "=" * 70)
    print("✅ Advanced ML forecasting complete!")
    print("=" * 70)
    print("\nNote: For production use:")
    print("- Install TensorFlow: pip install tensorflow")
    print("- Install XGBoost: pip install xgboost")
    print("- Tune hyperparameters for your specific data")


if __name__ == "__main__":
    main()
