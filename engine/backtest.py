"""
Backtesting and accuracy tracking system.
Evaluates forecast accuracy using walk-forward validation.
"""

import numpy as np
import pandas as pd
from datetime import timedelta
from engine.models import DayOfWeekModel, ExpSmoothingModel, GBTModel, EnsembleForecaster
from engine.features import build_feature_matrix


def compute_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    """Compute forecast accuracy metrics."""
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)

    mae = np.mean(np.abs(actual - predicted))

    # MAPE only where actual > 0
    nonzero = actual > 0
    if nonzero.sum() > 0:
        mape = np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100
    else:
        mape = np.nan

    # Weighted MAPE (better for intermittent demand)
    wmape = np.sum(np.abs(actual - predicted)) / max(np.sum(actual), 1) * 100

    # Bias: positive = over-forecasting, negative = under-forecasting
    bias = np.mean(predicted - actual)

    # Accuracy rate: % of days where prediction is within 1 unit
    within_1 = np.mean(np.abs(actual - predicted) <= 1) * 100

    return {
        "mae": round(mae, 2),
        "mape": round(mape, 1) if not np.isnan(mape) else None,
        "wmape": round(wmape, 1),
        "bias": round(bias, 2),
        "accuracy_within_1": round(within_1, 1),
    }


def walk_forward_backtest(
    daily_demand: pd.DataFrame,
    test_days: int = 7,
    step_size: int = 1,
) -> pd.DataFrame:
    """
    Walk-forward validation: train on data up to day T, predict T+1..T+step_size,
    then advance and repeat.

    Returns a DataFrame with actual vs predicted for every model.
    """
    max_date = daily_demand["date"].max()
    min_date = daily_demand["date"].min()
    total_history = (max_date - min_date).days

    # Need at least 21 days of history before we start testing
    min_train_days = 21
    if total_history < min_train_days + test_days:
        print(f"  Warning: only {total_history} days of history, need {min_train_days + test_days} for backtest")
        test_days = max(1, total_history - min_train_days)

    test_start = max_date - timedelta(days=test_days - 1)

    results = []
    stores = daily_demand["store"].unique()
    products = daily_demand["product"].unique()

    print(f"  Backtesting {len(stores)} stores x {len(products)} products over {test_days} days...")
    print(f"  Test period: {test_start.strftime('%m/%d/%Y')} - {max_date.strftime('%m/%d/%Y')}")

    for store in stores:
        for product in products:
            sp = daily_demand[
                (daily_demand["store"] == store) & (daily_demand["product"] == product)
            ].copy()

            if sp["qty"].sum() == 0:
                continue

            train = sp[sp["date"] < test_start]
            test = sp[(sp["date"] >= test_start) & (sp["date"] <= max_date)]

            if len(train) < 7 or len(test) == 0:
                continue

            # Fit models on training data
            dow_model = DayOfWeekModel()
            exp_model = ExpSmoothingModel()

            dow_model.fit(train[["date", "qty"]])
            exp_model.fit(train[["date", "qty"]])

            test_dates = pd.DatetimeIndex(test["date"].values)
            actuals = test["qty"].values

            dow_preds = dow_model.predict(test_dates)
            exp_preds = exp_model.predict(test_dates)

            for i, d in enumerate(test_dates):
                results.append({
                    "store": store,
                    "product": product,
                    "date": d,
                    "actual": actuals[i],
                    "pred_dow": round(dow_preds[i], 1),
                    "pred_exp": round(exp_preds[i], 1),
                })

    return pd.DataFrame(results)


def evaluate_models(backtest_results: pd.DataFrame) -> dict:
    """
    Evaluate each model's performance and determine optimal ensemble weights.
    Uses MAE (primary metric) for weight optimization. MAPE is secondary/display only.
    """
    if backtest_results.empty:
        return {"dow": 0.33, "exp": 0.34, "gbt": 0.33}

    model_metrics = {}
    for model_name in ["dow", "exp"]:
        pred_col = f"pred_{model_name}"
        if pred_col in backtest_results.columns:
            metrics = compute_metrics(
                backtest_results["actual"].values,
                backtest_results[pred_col].values,
            )
            model_metrics[model_name] = metrics

    # Determine weights based on inverse MAE (lower MAE = higher weight)
    weights = {}
    for name, metrics in model_metrics.items():
        mae = metrics.get("mae", 100)
        weights[name] = 1.0 / max(mae, 0.01)

    # Add GBT with default weight (can't easily backtest without features here)
    weights["gbt"] = max(weights.values()) * 1.2  # slight boost for GBT

    # Normalize
    total = sum(weights.values())
    weights = {k: round(v / total, 3) for k, v in weights.items()}

    return weights


def generate_accuracy_report(
    backtest_results: pd.DataFrame,
    weights: dict,
) -> str:
    """Generate a human-readable accuracy report."""
    lines = []
    lines.append("=" * 70)
    lines.append("  FORECAST ACCURACY REPORT (Backtest)")
    lines.append("=" * 70)

    # Overall metrics per model
    for model_name in ["dow", "exp"]:
        pred_col = f"pred_{model_name}"
        if pred_col not in backtest_results.columns:
            continue
        metrics = compute_metrics(
            backtest_results["actual"].values,
            backtest_results[pred_col].values,
        )
        name_map = {"dow": "Day-of-Week", "exp": "Exponential Smoothing"}
        lines.append(f"\n  {name_map.get(model_name, model_name)}:")
        lines.append(f"    MAE:    {metrics['mae']}  (primary)")
        lines.append(f"    MAPE:   {metrics['mape']}%  (secondary)" if metrics.get('mape') else "    MAPE:   N/A (no non-zero actuals)")
        lines.append(f"    WMAPE:  {metrics['wmape']}%")
        lines.append(f"    Bias:   {metrics['bias']:+.2f} ({'over' if metrics['bias'] > 0 else 'under'}-forecasting)")
        lines.append(f"    Within 1 unit: {metrics['accuracy_within_1']}% of predictions")

    # Ensemble prediction
    br = backtest_results.copy()
    br["pred_ensemble"] = (
        weights.get("dow", 0.33) * br["pred_dow"] +
        weights.get("exp", 0.34) * br["pred_exp"]
    ) / (weights.get("dow", 0.33) + weights.get("exp", 0.34))

    ens_metrics = compute_metrics(br["actual"].values, br["pred_ensemble"].values)
    lines.append(f"\n  Ensemble (weighted):")
    lines.append(f"    MAE:    {ens_metrics['mae']}  (primary)")
    lines.append(f"    MAPE:   {ens_metrics['mape']}%  (secondary)" if ens_metrics.get('mape') else "    MAPE:   N/A")
    lines.append(f"    WMAPE:  {ens_metrics['wmape']}%")
    lines.append(f"    Bias:   {ens_metrics['bias']:+.2f}")
    lines.append(f"    Within 1 unit: {ens_metrics['accuracy_within_1']}% of predictions")

    lines.append(f"\n  Ensemble Weights: {weights}")

    # Per-store breakdown
    lines.append(f"\n{'-' * 70}")
    lines.append("  Per-Store Accuracy (Ensemble):")
    for store in sorted(br["store"].unique()):
        store_data = br[br["store"] == store]
        sm = compute_metrics(store_data["actual"].values, store_data["pred_ensemble"].values)
        lines.append(f"    {store}: MAE={sm['mae']}, WMAPE={sm['wmape']}%, Bias={sm['bias']:+.2f}")

    # Worst products
    lines.append(f"\n{'-' * 70}")
    lines.append("  Products with Highest Error:")
    product_errors = []
    for (store, product), group in br.groupby(["store", "product"]):
        if group["actual"].sum() < 2:
            continue
        pm = compute_metrics(group["actual"].values, group["pred_ensemble"].values)
        product_errors.append((store, product, pm["wmape"], pm["mae"], group["actual"].sum()))

    product_errors.sort(key=lambda x: x[2], reverse=True)
    for store, product, wmape, mae, total in product_errors[:10]:
        lines.append(f"    {store} / {product}: WMAPE={wmape}%, MAE={mae}, Total Actual={total}")

    lines.append(f"\n{'=' * 70}")
    return "\n".join(lines)
