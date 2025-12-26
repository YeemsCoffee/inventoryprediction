#!/usr/bin/env python3
"""
Validate TFT predictions against actual sales data.
Compares predictions vs actuals for recent dates to assess model accuracy.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.database import RDSConnector

# Use PST timezone to match business operations
PST = ZoneInfo('America/Los_Angeles')


def calculate_metrics(actuals, predictions):
    """Calculate accuracy metrics."""
    mae = np.mean(np.abs(actuals - predictions))
    rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
    mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100 if actuals.mean() > 0 else 0

    return {
        'mae': mae,
        'rmse': rmse,
        'mape': mape
    }


def validate_predictions(lookback_days=7):
    """
    Validate predictions against actual sales.

    Args:
        lookback_days: Number of recent days to validate (default 7)
    """

    db = RDSConnector()

    print("=" * 80)
    print("🔍 PREDICTION VALIDATION REPORT")
    print("=" * 80)

    # Use PST timezone for all date calculations to match business operations
    now_pst = datetime.now(PST)
    print(f"Generated: {now_pst.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Validation Period: Last {lookback_days} days")
    print()

    # Calculate date range for validation using PST
    end_date = now_pst.date()
    start_date = end_date - timedelta(days=lookback_days)

    print(f"Comparing predictions vs actuals from {start_date} to {end_date} (PST)")
    print()

    # 1. Get actual sales data
    print("📊 Loading actual sales data...")
    actuals_query = f"""
    SELECT
        d.date,
        p.product_name,
        l.location_name as location,
        SUM(f.quantity) as actual_quantity
    FROM gold.fact_sales f
    JOIN gold.dim_date d ON f.date_key = d.date_key
    JOIN gold.dim_product p ON f.product_sk = p.product_sk
    JOIN gold.dim_location l ON f.location_sk = l.location_sk
    WHERE d.date >= '{start_date}' AND d.date <= '{end_date}'
    GROUP BY d.date, p.product_name, l.location_name
    ORDER BY d.date, l.location_name, p.product_name
    """

    with db.engine.connect() as conn:
        actuals_df = pd.read_sql(actuals_query, conn)

    print(f"✅ Loaded {len(actuals_df):,} actual sales records")
    print()

    # 2. Get predictions for the same period
    print("🔮 Loading predictions...")
    predictions_query = f"""
    SELECT
        forecast_date as date,
        product_name,
        location,
        forecasted_quantity as predicted_quantity
    FROM predictions.demand_forecasts
    WHERE forecast_date >= '{start_date}' AND forecast_date <= '{end_date}'
    ORDER BY forecast_date, location, product_name
    """

    with db.engine.connect() as conn:
        predictions_df = pd.read_sql(predictions_query, conn)

    print(f"✅ Loaded {len(predictions_df):,} prediction records")
    print()

    # 3. Merge actuals and predictions
    print("🔗 Matching predictions with actuals...")

    # Ensure date columns are datetime
    actuals_df['date'] = pd.to_datetime(actuals_df['date'])
    predictions_df['date'] = pd.to_datetime(predictions_df['date'])

    # Merge on date, product, location
    comparison_df = pd.merge(
        actuals_df,
        predictions_df,
        on=['date', 'product_name', 'location'],
        how='inner'
    )

    if len(comparison_df) == 0:
        print("⚠️  No matching predictions found for the validation period.")
        print("   This is expected if predictions only cover future dates.")
        print("   Try running the pipeline with historical dates or wait for actuals to accumulate.")
        return

    print(f"✅ Matched {len(comparison_df):,} prediction-actual pairs")
    print()

    # 4. Calculate overall metrics
    print("=" * 80)
    print("📈 OVERALL VALIDATION METRICS")
    print("=" * 80)

    overall_metrics = calculate_metrics(
        comparison_df['actual_quantity'],
        comparison_df['predicted_quantity']
    )

    print(f"Mean Absolute Error (MAE):    {overall_metrics['mae']:>10.2f} units/day")
    print(f"Root Mean Squared Error (RMSE): {overall_metrics['rmse']:>10.2f} units/day")
    print(f"Mean Absolute % Error (MAPE):  {overall_metrics['mape']:>10.2f}%")
    print()

    # 5. Calculate metrics per product-location
    print("=" * 80)
    print("📊 METRICS BY PRODUCT & LOCATION")
    print("=" * 80)
    print()

    grouped = comparison_df.groupby(['product_name', 'location'])

    results = []
    for (product, location), group in grouped:
        metrics = calculate_metrics(group['actual_quantity'], group['predicted_quantity'])
        avg_actual = group['actual_quantity'].mean()
        avg_predicted = group['predicted_quantity'].mean()

        results.append({
            'product': product,
            'location': location,
            'samples': len(group),
            'avg_actual': avg_actual,
            'avg_predicted': avg_predicted,
            'mae': metrics['mae'],
            'rmse': metrics['rmse'],
            'mape': metrics['mape']
        })

    results_df = pd.DataFrame(results).sort_values('mae')

    print(f"{'Product':<40} {'Location':<15} {'MAE':>8} {'MAPE':>8} {'Avg Actual':>12} {'Avg Pred':>12}")
    print("-" * 110)

    for _, row in results_df.iterrows():
        print(f"{row['product'][:40]:<40} {row['location']:<15} "
              f"{row['mae']:>8.1f} {row['mape']:>7.1f}% "
              f"{row['avg_actual']:>12.1f} {row['avg_predicted']:>12.1f}")

    print()

    # 6. Identify best and worst performers
    print("=" * 80)
    print("🏆 BEST PREDICTIONS (Lowest MAE)")
    print("=" * 80)

    best_3 = results_df.head(3)
    for i, row in enumerate(best_3.itertuples(), 1):
        print(f"{i}. {row.product} @ {row.location}")
        print(f"   MAE: {row.mae:.1f} | MAPE: {row.mape:.1f}% | Avg Daily: {row.avg_actual:.1f}")
        print()

    print("=" * 80)
    print("⚠️  WORST PREDICTIONS (Highest MAE)")
    print("=" * 80)

    worst_3 = results_df.tail(3).iloc[::-1]  # Reverse to show worst first
    for i, row in enumerate(worst_3.itertuples(), 1):
        print(f"{i}. {row.product} @ {row.location}")
        print(f"   MAE: {row.mae:.1f} | MAPE: {row.mape:.1f}% | Avg Daily: {row.avg_actual:.1f}")
        print(f"   ⚠️  Consider: More data, different features, or model tuning")
        print()

    # 7. Check for systematic biases
    print("=" * 80)
    print("🔎 BIAS ANALYSIS")
    print("=" * 80)

    comparison_df['error'] = comparison_df['predicted_quantity'] - comparison_df['actual_quantity']
    comparison_df['abs_error'] = np.abs(comparison_df['error'])
    comparison_df['pct_error'] = (comparison_df['error'] / comparison_df['actual_quantity']) * 100

    avg_bias = comparison_df['error'].mean()
    avg_pct_bias = comparison_df['pct_error'].mean()

    print(f"Average Bias: {avg_bias:>10.2f} units/day")
    print(f"Average % Bias: {avg_pct_bias:>10.2f}%")
    print()

    if avg_bias > 10:
        print("⚠️  OVER-FORECASTING: Predictions tend to be higher than actuals")
        print("   → May lead to over-ordering materials")
    elif avg_bias < -10:
        print("⚠️  UNDER-FORECASTING: Predictions tend to be lower than actuals")
        print("   → May lead to stockouts")
    else:
        print("✅ BALANCED: No significant systematic bias detected")

    print()

    # 8. Daily comparison sample
    print("=" * 80)
    print("📅 SAMPLE: Recent Daily Comparison (Last 3 Days)")
    print("=" * 80)
    print()

    recent_dates = comparison_df['date'].nlargest(3).unique()
    sample = comparison_df[comparison_df['date'].isin(recent_dates)].head(10)

    print(f"{'Date':<12} {'Product':<30} {'Location':<12} {'Actual':>8} {'Predicted':>10} {'Error':>8}")
    print("-" * 90)

    for _, row in sample.iterrows():
        error = row['predicted_quantity'] - row['actual_quantity']
        print(f"{row['date'].strftime('%Y-%m-%d'):<12} "
              f"{row['product_name'][:30]:<30} "
              f"{row['location']:<12} "
              f"{row['actual_quantity']:>8.0f} "
              f"{row['predicted_quantity']:>10.1f} "
              f"{error:>8.1f}")

    print()

    # 9. Summary and recommendations
    print("=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    print()

    if overall_metrics['mape'] < 15:
        print("✅ EXCELLENT: MAPE < 15% - Predictions are highly accurate")
    elif overall_metrics['mape'] < 25:
        print("✅ GOOD: MAPE < 25% - Predictions are acceptable for business use")
    elif overall_metrics['mape'] < 35:
        print("⚠️  MODERATE: MAPE < 35% - Predictions usable but could improve")
        print("   → Consider adding more features or increasing training data")
    else:
        print("⚠️  POOR: MAPE > 35% - Predictions need improvement")
        print("   → Review model parameters, add features, or get more training data")

    print()
    print("Next Steps:")
    print("  1. Focus on improving high-error products (see worst performers above)")
    print("  2. Investigate products with MAPE > 30%")
    print("  3. Consider adding more location-specific features")
    print("  4. Run validation weekly to track model drift")
    print()

    print("=" * 80)
    print("✅ Validation Complete")
    print("=" * 80)
    print()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Validate TFT predictions against actuals')
    parser.add_argument('--days', type=int, default=7,
                        help='Number of recent days to validate (default: 7)')

    args = parser.parse_args()

    validate_predictions(lookback_days=args.days)
