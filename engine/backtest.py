"""
Backtesting and accuracy tracking system.
Evaluates forecast accuracy using walk-forward validation.

Lane-aware: each product is classified into the same lane as production
(daily / periodic / intermittent / dormant) using training data only,
so reported metrics reflect actual live forecast behaviour.
"""

import numpy as np
import pandas as pd
from datetime import timedelta
from engine.models import DayOfWeekModel, ExpSmoothingModel
from engine.router import classify_lane, predict_intermittent, predict_periodic


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
    Walk-forward validation: train on data up to day T, predict T+1..T+test_days.

    Each product is classified into its forecast lane using **training data only**
    (no look-ahead), and evaluated with the same logic as production:

    - Lane 1 (daily):       DOW model + Exp Smoothing (stored as pred_dow / pred_exp).
                            pred_lane is filled by generate_accuracy_report using weights.
    - Lane 2 (periodic):    predict_periodic on training data → pred_lane.
    - Lane 3 (intermittent): predict_intermittent on training data → pred_lane.
    - Lane 4 (dormant):     pred_lane = 0.

    Returns a DataFrame with columns:
        store, product, date, actual, lane, pred_lane, pred_dow, pred_exp
    pred_dow / pred_exp are NaN for non-daily products.
    pred_lane is NaN for daily products (filled later using ensemble weights).
    """
    max_date = daily_demand["date"].max()
    min_date = daily_demand["date"].min()
    total_history = (max_date - min_date).days

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

    lane_counts = {"daily": 0, "periodic": 0, "intermittent": 0, "dormant": 0}

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

            # Classify using training data only — same window as production
            lane = classify_lane(product, train)
            lane_counts[lane] += 1

            test_dates = pd.DatetimeIndex(test["date"].values)
            actuals = test["qty"].values
            num_test = len(test)
            base = {"store": store, "product": product, "lane": lane}

            # Lane 4 — Dormant
            if lane == "dormant":
                for i, d in enumerate(test_dates):
                    results.append({**base, "date": d, "actual": actuals[i],
                                    "pred_lane": 0.0,
                                    "pred_dow": np.nan, "pred_exp": np.nan})
                continue

            # Lane 3 — Intermittent
            if lane == "intermittent":
                preds = predict_intermittent(train, num_test)
                for i, d in enumerate(test_dates):
                    results.append({**base, "date": d, "actual": actuals[i],
                                    "pred_lane": round(float(preds[i]), 2),
                                    "pred_dow": np.nan, "pred_exp": np.nan})
                continue

            # Lane 2 — Periodic
            if lane == "periodic":
                preds = predict_periodic(train, num_test)
                for i, d in enumerate(test_dates):
                    results.append({**base, "date": d, "actual": actuals[i],
                                    "pred_lane": round(float(preds[i]), 2),
                                    "pred_dow": np.nan, "pred_exp": np.nan})
                continue

            # Lane 1 — Daily: DOW + Exp Smoothing
            dow_model = DayOfWeekModel()
            exp_model = ExpSmoothingModel()
            dow_model.fit(train[["date", "qty"]])
            exp_model.fit(train[["date", "qty"]])

            dow_preds = dow_model.predict(test_dates)
            exp_preds = exp_model.predict(test_dates)

            for i, d in enumerate(test_dates):
                results.append({**base, "date": d, "actual": actuals[i],
                                 "pred_lane": np.nan,   # filled by generate_accuracy_report
                                 "pred_dow": round(dow_preds[i], 1),
                                 "pred_exp": round(exp_preds[i], 1)})

    if results:
        counts_str = ", ".join(f"{v} {k}" for k, v in lane_counts.items() if v > 0)
        print(f"  Lane assignments: {counts_str}")

    return pd.DataFrame(results)


def evaluate_models(backtest_results: pd.DataFrame) -> dict:
    """
    Evaluate DOW vs Exp Smoothing on daily-lane products only and return
    optimal ensemble weights. Non-daily products don't use the ensemble
    so including them would bias the weights.
    """
    if backtest_results.empty:
        return {"dow": 0.33, "exp": 0.34, "gbt": 0.33}

    daily = backtest_results[backtest_results["lane"] == "daily"].dropna(subset=["pred_dow", "pred_exp"])
    if daily.empty:
        return {"dow": 0.33, "exp": 0.34, "gbt": 0.33}

    model_metrics = {}
    for model_name in ["dow", "exp"]:
        pred_col = f"pred_{model_name}"
        metrics = compute_metrics(daily["actual"].values, daily[pred_col].values)
        model_metrics[model_name] = metrics

    weights = {}
    for name, metrics in model_metrics.items():
        wmape = metrics.get("wmape", 100)
        weights[name] = 1.0 / max(wmape, 1)

    # GBT gets a slight boost since it can't be backtested here
    weights["gbt"] = max(weights.values()) * 1.2

    total = sum(weights.values())
    weights = {k: round(v / total, 3) for k, v in weights.items()}
    return weights


def generate_accuracy_report(
    backtest_results: pd.DataFrame,
    weights: dict,
) -> str:
    """
    Generate a human-readable accuracy report broken down by forecast lane.

    Structure:
    - Lane distribution summary
    - Lane 1 (Daily): DOW / ExpSmoothing / Ensemble breakdown + weights
    - Lane 2 (Periodic): metrics using lane prediction
    - Lane 3 (Intermittent): metrics using lane prediction
    - Lane 4 (Dormant): metrics (prediction = 0)
    - Overall (all non-dormant lanes combined)
    - Per-store accuracy
    - Products with highest error
    """
    lines = []
    lines.append("=" * 70)
    lines.append("  FORECAST ACCURACY REPORT (Backtest)")
    lines.append("=" * 70)

    if backtest_results.empty:
        lines.append("\n  No backtest results available.")
        lines.append("=" * 70)
        return "\n".join(lines)

    br = backtest_results.copy()

    # Fill pred_lane for daily products using ensemble weights
    daily_mask = br["lane"] == "daily"
    if daily_mask.any():
        dw = weights.get("dow", 0.33)
        ew = weights.get("exp", 0.34)
        total_de = dw + ew
        br.loc[daily_mask, "pred_lane"] = (
            dw * br.loc[daily_mask, "pred_dow"] +
            ew * br.loc[daily_mask, "pred_exp"]
        ) / total_de

    # Lane distribution (unique store-product pairs per lane)
    dist_parts = []
    for lane_name in ["daily", "periodic", "intermittent", "dormant"]:
        n = br[br["lane"] == lane_name].groupby(["store", "product"]).ngroups
        if n > 0:
            dist_parts.append(f"{n} {lane_name}")
    lines.append(f"\n  Lane distribution: {', '.join(dist_parts)}")

    # ── Lane 1: Daily ────────────────────────────────────────────────
    daily_br = br[daily_mask]
    if not daily_br.empty:
        lines.append(f"\n{'-' * 70}")
        n_daily = daily_br.groupby(["store", "product"]).ngroups
        lines.append(f"  Lane 1 — Daily ML ({n_daily} products):")
        for model_name, label in [("dow", "Day-of-Week"), ("exp", "Exp Smoothing")]:
            pred_col = f"pred_{model_name}"
            valid = daily_br.dropna(subset=[pred_col])
            if not valid.empty:
                m = compute_metrics(valid["actual"].values, valid[pred_col].values)
                lines.append(f"    {label}:      MAE={m['mae']}  WMAPE={m['wmape']}%  "
                              f"Bias={m['bias']:+.2f}  Within1={m['accuracy_within_1']}%")

        ens_m = compute_metrics(daily_br["actual"].values, daily_br["pred_lane"].values)
        lines.append(f"    Ensemble:        MAE={ens_m['mae']}  WMAPE={ens_m['wmape']}%  "
                     f"Bias={ens_m['bias']:+.2f}  Within1={ens_m['accuracy_within_1']}%")
        lines.append(f"    Weights: DOW={weights.get('dow', '?')}  "
                     f"ExpSmooth={weights.get('exp', '?')}  GBT={weights.get('gbt', '?')}")

    # ── Lane 2: Periodic ─────────────────────────────────────────────
    periodic_br = br[br["lane"] == "periodic"]
    if not periodic_br.empty:
        lines.append(f"\n{'-' * 70}")
        n = periodic_br.groupby(["store", "product"]).ngroups
        m = compute_metrics(periodic_br["actual"].values, periodic_br["pred_lane"].values)
        lines.append(f"  Lane 2 — Periodic ({n} products):")
        lines.append(f"    MAE={m['mae']}  WMAPE={m['wmape']}%  "
                     f"Bias={m['bias']:+.2f}  Within1={m['accuracy_within_1']}%")

    # ── Lane 3: Intermittent ─────────────────────────────────────────
    intermittent_br = br[br["lane"] == "intermittent"]
    if not intermittent_br.empty:
        lines.append(f"\n{'-' * 70}")
        n = intermittent_br.groupby(["store", "product"]).ngroups
        m = compute_metrics(intermittent_br["actual"].values, intermittent_br["pred_lane"].values)
        lines.append(f"  Lane 3 — Intermittent ({n} products):")
        lines.append(f"    MAE={m['mae']}  WMAPE={m['wmape']}%  "
                     f"Bias={m['bias']:+.2f}  Within1={m['accuracy_within_1']}%")

    # ── Lane 4: Dormant ──────────────────────────────────────────────
    dormant_br = br[br["lane"] == "dormant"]
    if not dormant_br.empty:
        lines.append(f"\n{'-' * 70}")
        n = dormant_br.groupby(["store", "product"]).ngroups
        m = compute_metrics(dormant_br["actual"].values, dormant_br["pred_lane"].values)
        lines.append(f"  Lane 4 — Dormant ({n} products, predicting zero):")
        lines.append(f"    MAE={m['mae']}  WMAPE={m['wmape']}%  Bias={m['bias']:+.2f}")

    # ── Overall (non-dormant) ─────────────────────────────────────────
    active_br = br[br["lane"] != "dormant"]
    if not active_br.empty:
        lines.append(f"\n{'-' * 70}")
        m = compute_metrics(active_br["actual"].values, active_br["pred_lane"].values)
        lines.append(f"  Overall (non-dormant lanes):")
        lines.append(f"    MAE={m['mae']}  WMAPE={m['wmape']}%  "
                     f"Bias={m['bias']:+.2f}  Within1={m['accuracy_within_1']}%")

    # ── Per-store ─────────────────────────────────────────────────────
    lines.append(f"\n{'-' * 70}")
    lines.append("  Per-Store Accuracy (non-dormant):")
    for store in sorted(active_br["store"].unique()):
        sd = active_br[active_br["store"] == store]
        sm = compute_metrics(sd["actual"].values, sd["pred_lane"].values)
        lines.append(f"    {store}: MAE={sm['mae']}, WMAPE={sm['wmape']}%, Bias={sm['bias']:+.2f}")

    # ── Worst products ────────────────────────────────────────────────
    lines.append(f"\n{'-' * 70}")
    lines.append("  Products with Highest Error:")
    product_errors = []
    for (store, product), group in active_br.groupby(["store", "product"]):
        if group["actual"].sum() < 2:
            continue
        pm = compute_metrics(group["actual"].values, group["pred_lane"].values)
        lane_label = group["lane"].iloc[0]
        product_errors.append((store, product, pm["wmape"], pm["mae"],
                                group["actual"].sum(), lane_label))

    product_errors.sort(key=lambda x: x[2], reverse=True)
    for store, product, wmape, mae, total, lane_label in product_errors[:10]:
        lines.append(f"    [{lane_label}] {store} / {product}: "
                     f"WMAPE={wmape}%, MAE={mae}, Total Actual={total:.0f}")

    lines.append(f"\n{'=' * 70}")
