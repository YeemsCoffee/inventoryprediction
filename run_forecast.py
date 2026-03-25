#!/usr/bin/env python3
"""
Inventory Prediction System v2
Enterprise-grade demand forecasting with ensemble models, backtesting, and feedback loops.

Usage:
    python run_forecast.py                    # Generate 14-day forecast
    python run_forecast.py --days 7           # Generate 7-day forecast
    python run_forecast.py --backtest         # Run backtest and show accuracy report
    python run_forecast.py --update-actuals   # Feed actual sales back into the system
    python run_forecast.py --feedback-report  # Show feedback loop report
"""

import sys
import os
import argparse
import numpy as np
import pandas as pd
from datetime import timedelta

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.ingest import load_all_data, build_daily_demand
from engine.features import build_feature_matrix
from engine.models import DayOfWeekModel, ExpSmoothingModel, GBTModel, EnsembleForecaster
from engine.backtest import walk_forward_backtest, evaluate_models, generate_accuracy_report
from engine.feedback import (
    compute_correction_factors, record_forecasts_batch, update_actuals,
    generate_feedback_report, export_feedback_to_excel,
)
from engine.packing import apply_safety_stock, generate_packing_list_csv, print_packing_list, load_par_levels
from config.products import STORES


def run_backtest(data_dir: str = "."):
    """Run backtesting and print accuracy report."""
    print("\n[1/3] Loading data...")
    raw = load_all_data(data_dir)
    print(f"  Total records: {len(raw)}")

    print("\n[2/3] Building daily demand...")
    daily = build_daily_demand(raw)

    print("\n[3/3] Running walk-forward backtest...")
    results = walk_forward_backtest(daily, test_days=7)

    weights = evaluate_models(results)
    report = generate_accuracy_report(results, weights)
    print(report)

    return weights


def run_forecast(data_dir: str = ".", num_days: int = 14, output_dir: str = "output"):
    """Run the full forecasting pipeline."""
    print("\n" + "=" * 70)
    print("  INVENTORY PREDICTION SYSTEM v2")
    print("=" * 70)

    # --- Step 1: Load data ---
    print("\n[1/6] Loading data...")
    raw = load_all_data(data_dir)
    print(f"  Total records: {len(raw)}")
    print(f"  Date range: {raw['date'].min().strftime('%m/%d/%Y')} - {raw['date'].max().strftime('%m/%d/%Y')}")
    print(f"  Stores: {', '.join(sorted(raw['store'].unique()))}")
    print(f"  Products: {len(raw['product'].unique())}")

    # --- Step 2: Build daily demand ---
    print("\n[2/6] Building daily demand matrix...")
    daily = build_daily_demand(raw)

    # --- Step 3: Feature engineering ---
    print("\n[3/6] Engineering features...")
    features = build_feature_matrix(daily)

    # --- Step 4: Backtest to determine model weights ---
    print("\n[4/6] Backtesting models to determine ensemble weights...")
    bt_results = walk_forward_backtest(daily, test_days=7)
    weights = evaluate_models(bt_results)
    print(f"  Ensemble weights: DOW={weights['dow']:.0%}, ExpSmooth={weights['exp']:.0%}, GBT={weights['gbt']:.0%}")

    # --- Step 5: Train and predict ---
    print("\n[5/6] Training models and generating forecasts...")
    forecast_start = daily["date"].max() + timedelta(days=1)
    forecast_dates = pd.date_range(forecast_start, periods=num_days, freq="D")

    stores = sorted(daily["store"].unique())
    products = sorted(daily["product"].unique())

    # Train GBT globally
    gbt = GBTModel()
    gbt.fit(features)

    # Get correction factors from feedback loop
    corrections = compute_correction_factors()

    predictions = {}  # (store, product) -> np.array

    for store in stores:
        for product in products:
            sp_demand = daily[
                (daily["store"] == store) & (daily["product"] == product)
            ]

            # Per-product models
            dow_model = DayOfWeekModel()
            exp_model = ExpSmoothingModel()
            dow_model.fit(sp_demand[["date", "qty"]])
            exp_model.fit(sp_demand[["date", "qty"]])

            dow_preds = dow_model.predict(forecast_dates)
            exp_preds = exp_model.predict(forecast_dates)

            # Build feature rows for GBT prediction on future dates
            future_features = _build_future_features(sp_demand, features, store, product, forecast_dates)
            if future_features is not None and gbt.is_fitted:
                gbt_preds = gbt.predict(future_features)
            else:
                gbt_preds = np.zeros(num_days)

            # Ensemble
            ensemble_preds = (
                weights["dow"] * dow_preds +
                weights["exp"] * exp_preds +
                weights["gbt"] * gbt_preds
            )
            ensemble_preds = np.maximum(0, ensemble_preds)

            # Apply feedback correction
            correction = corrections.get((store, product), 1.0)
            ensemble_preds *= correction

            predictions[(store, product)] = ensemble_preds

    # --- Step 6: Apply safety stock and generate output ---
    print("\n[6/6] Applying safety stock and generating packing lists...")
    predictions = apply_safety_stock(predictions, daily)

    # Load par levels if the file exists
    par_xlsx = os.path.join(data_dir, "Store Max Items.xlsx")
    par_levels = load_par_levels(par_xlsx) if os.path.exists(par_xlsx) else None
    if par_levels:
        print(f"  Loaded par levels for {len(par_levels)} store/product combinations.")
    else:
        print("  No par levels file found — skipping par cap.")

    # Print to console
    for store in stores:
        print_packing_list(predictions, forecast_dates, store, par_levels=par_levels)

    # Export CSVs
    print()
    filepaths = generate_packing_list_csv(predictions, forecast_dates, stores, output_dir, par_levels=par_levels)

    # Record forecasts for feedback loop (single batch write)
    forecast_entries = []
    for (store, product), preds in predictions.items():
        for i, d in enumerate(forecast_dates):
            forecast_entries.append((store, product, d.strftime("%Y-%m-%d"), round(float(preds[i]), 2)))
    record_forecasts_batch(forecast_entries)

    print(f"\n  Forecast period: {forecast_dates[0].strftime('%m/%d/%Y')} - {forecast_dates[-1].strftime('%m/%d/%Y')}")
    print(f"  Output saved to: {output_dir}/")

    # Show backtest accuracy
    report = generate_accuracy_report(bt_results, weights)
    print(report)

    # Export feedback report to Excel
    result = export_feedback_to_excel(output_path=os.path.join(output_dir, "feedback_report.xlsx"))
    if result:
        print(f"\n  Excel report saved to: {result}")

    return predictions


def _build_future_features(
    sp_demand: pd.DataFrame,
    all_features: pd.DataFrame,
    store: str,
    product: str,
    forecast_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Build feature rows for future dates for GBT prediction."""
    if sp_demand["qty"].sum() == 0:
        return None

    rows = []
    sp = sp_demand.sort_values("date")
    last_qty = sp["qty"].iloc[-1] if len(sp) > 0 else 0
    recent_7 = sp["qty"].tail(7)
    recent_14 = sp["qty"].tail(14)
    recent_28 = sp["qty"].tail(28)

    hist_avg = sp["qty"].mean()
    hist_std = sp["qty"].std() if len(sp) > 1 else 0
    cv = (hist_std / hist_avg) if hist_avg > 0 else 0
    order_freq = (sp["qty"] > 0).mean()

    rm7 = recent_7.mean()
    rm14 = recent_14.mean()
    rm28 = recent_28.mean()
    rs7 = recent_7.std() if len(recent_7) > 1 else 0
    rs14 = recent_14.std() if len(recent_14) > 1 else 0
    rmax7 = recent_7.max()
    trend = (rm7 / rm28) if rm28 > 0 else 1.0

    last_order_date = sp[sp["qty"] > 0]["date"].max() if (sp["qty"] > 0).any() else sp["date"].min()

    for i, d in enumerate(forecast_dates):
        dow = d.dayofweek
        row = {
            "dow": dow,
            "day_of_month": d.day,
            "is_weekend": int(dow >= 5),
            "is_monday": int(dow == 0),
            "is_friday": int(dow == 4),
            "dow_sin": np.sin(2 * np.pi * dow / 7),
            "dow_cos": np.cos(2 * np.pi * dow / 7),
            "dom_sin": np.sin(2 * np.pi * d.day / 31),
            "dom_cos": np.cos(2 * np.pi * d.day / 31),
            "lag_1": last_qty,
            "lag_7": recent_7.iloc[0] if len(recent_7) > 0 else 0,
            "lag_14": recent_14.iloc[0] if len(recent_14) > 0 else 0,
            "rolling_mean_7": rm7,
            "rolling_mean_14": rm14,
            "rolling_mean_28": rm28,
            "rolling_std_7": rs7,
            "rolling_std_14": rs14,
            "rolling_max_7": rmax7,
            "trend_7_28": np.clip(trend, 0.2, 5.0),
            "days_since_last_order": (d - last_order_date).days if pd.notna(last_order_date) else 0,
            "product_hist_avg": hist_avg,
            "product_cv": np.clip(cv, 0, 10),
            "order_frequency": order_freq,
        }
        rows.append(row)

    return pd.DataFrame(rows)


def run_update_actuals(data_dir: str = "."):
    """Update feedback loop with actual sales data."""
    print("\n[1/2] Loading actual sales data...")
    raw = load_all_data(data_dir)
    daily = raw.groupby(["store", "product", "date"])["qty"].sum().reset_index()

    print(f"\n[2/2] Matching actuals against recorded forecasts...")
    updated = update_actuals(daily)
    print(f"  Updated {updated} forecast entries with actual data.")

    report = generate_feedback_report()
    print(report)

    result = export_feedback_to_excel(output_path="output/feedback_report.xlsx")
    if result:
        print(f"\n  Excel report saved to: {result}")


def main():
    parser = argparse.ArgumentParser(description="Inventory Prediction System v2")
    parser.add_argument("--days", type=int, default=14, help="Number of days to forecast")
    parser.add_argument("--data-dir", type=str, default=".", help="Directory with sales CSV files")
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory for CSVs")
    parser.add_argument("--backtest", action="store_true", help="Run backtest only")
    parser.add_argument("--update-actuals", action="store_true", help="Update feedback with actual sales")
    parser.add_argument("--feedback-report", action="store_true", help="Show feedback loop report")
    parser.add_argument("--export-feedback", action="store_true", help="Export feedback history to Excel")

    args = parser.parse_args()

    if args.backtest:
        run_backtest(args.data_dir)
    elif args.update_actuals:
        run_update_actuals(args.data_dir)
    elif args.feedback_report:
        print(generate_feedback_report())
    elif args.export_feedback:
        out = os.path.join(args.output_dir, "feedback_report.xlsx")
        result = export_feedback_to_excel(output_path=out)
        if result:
            print(f"Feedback report exported to: {result}")
        else:
            print("No feedback history to export.")
    else:
        run_forecast(args.data_dir, args.days, args.output_dir)


if __name__ == "__main__":
    main()
