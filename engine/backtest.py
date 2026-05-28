"""
Backtesting and accuracy tracking system.
Evaluates forecast accuracy using walk-forward validation.

Lane-aware: each product is classified into the same lane as production
(daily / periodic / intermittent / dormant) using training data only,
so reported metrics reflect actual live forecast behaviour.

GBT is now trained and scored within the backtest — no heuristic weight boost.
"""

import numpy as np
import pandas as pd
from datetime import timedelta
from engine.models import DayOfWeekModel, ExpSmoothingModel, GBTModel
from engine.router import classify_lane, predict_intermittent, predict_periodic
from engine.features import build_future_features, build_feature_matrix
from config.products import FORECAST_CONFIG


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
    features_df: pd.DataFrame = None,
    test_days: int = 14,
    step_size: int = 1,
) -> pd.DataFrame:
    """
    Walk-forward validation: train on data up to day T, predict T+1..T+test_days.

    Each product is classified into its forecast lane using **training data only**
    (no look-ahead), and evaluated with the same logic as production:

    - Lane 1 (daily):        DOW + ExpSmoothing + GBT ensemble (same as live).
                             GBT trained on training-period daily-lane rows only.
    - Lane 2 (periodic):     predict_periodic on training data → pred_lane.
    - Lane 3 (intermittent): predict_intermittent on training data → pred_lane.
    - Lane 4 (dormant):      pred_lane = 0.

    features_df: pre-built feature matrix (from build_feature_matrix). If None,
                 built internally from daily_demand. Passing it in avoids
                 recomputing features on every backtest call.

    Returns a DataFrame with columns:
        store, product, date, actual, lane, pred_lane, pred_dow, pred_exp, pred_gbt
    pred_dow/pred_exp/pred_gbt are NaN for non-daily products.
    pred_lane for daily products is the weighted ensemble of all three.
    """
    max_date = daily_demand["date"].max()
    min_date = daily_demand["date"].min()
    total_history = (max_date - min_date).days

    min_train_days = 21
    if total_history < min_train_days + test_days:
        print(f"  Warning: only {total_history} days of history, need {min_train_days + test_days} for backtest")
        test_days = max(1, total_history - min_train_days)

    test_start = max_date - timedelta(days=test_days - 1)

    # Build features if not provided
    if features_df is None:
        features_df = build_feature_matrix(daily_demand)

    # Split features into train period only (no look-ahead for GBT)
    train_features = features_df[features_df["date"] < test_start].copy()

    stores = daily_demand["store"].unique()
    products = daily_demand["product"].unique()

    print(f"  Backtesting {len(stores)} stores x {len(products)} products over {test_days} days...")
    print(f"  Test period: {test_start.strftime('%m/%d/%Y')} - {max_date.strftime('%m/%d/%Y')}")

    # ── Pre-classify all lanes using training data only ──────────────────
    # Also collect daily-lane pairs for GBT training filter
    lane_map = {}
    lane_counts = {"daily": 0, "periodic": 0, "intermittent": 0, "dormant": 0}
    daily_lane_pairs = set()

    for store in stores:
        for product in products:
            sp = daily_demand[
                (daily_demand["store"] == store) & (daily_demand["product"] == product)
            ]
            train = sp[sp["date"] < test_start]
            if train["qty"].sum() == 0 and len(train) == 0:
                lane_map[(store, product)] = "dormant"
                continue
            lane = classify_lane(product, train)
            lane_map[(store, product)] = lane
            lane_counts[lane] += 1
            if lane == "daily":
                daily_lane_pairs.add((store, product))

    # ── Train GBT on daily-lane training rows only ────────────────────────
    # This matches production: GBT only serves daily-lane items, so training
    # on intermittent/periodic rows just adds noise.
    gbt = GBTModel()
    if daily_lane_pairs:
        def _is_daily_lane(row):
            return (row["store"], row["product"]) in daily_lane_pairs
        daily_train_features = train_features[
            train_features.apply(_is_daily_lane, axis=1)
        ]
        if len(daily_train_features) >= 20:
            gbt.fit(daily_train_features)

    counts_str = ", ".join(f"{v} {k}" for k, v in lane_counts.items() if v > 0)
    print(f"  Lane assignments: {counts_str}")
    print(f"  GBT trained on {len(daily_train_features) if daily_lane_pairs else 0} daily-lane rows")

    # ── Per-product prediction loop ───────────────────────────────────────
    results = []

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

            lane = lane_map.get((store, product), "dormant")
            test_dates = pd.DatetimeIndex(test["date"].values)
            actuals = test["qty"].values
            num_test = len(test)
            base = {"store": store, "product": product, "lane": lane}

            # Lane 4 — Dormant
            if lane == "dormant":
                for i, d in enumerate(test_dates):
                    results.append({**base, "date": d, "actual": actuals[i],
                                    "pred_lane": 0.0,
                                    "pred_dow": np.nan, "pred_exp": np.nan, "pred_gbt": np.nan})
                continue

            # Lane 3 — Intermittent
            if lane == "intermittent":
                preds = predict_intermittent(train, num_test)
                for i, d in enumerate(test_dates):
                    results.append({**base, "date": d, "actual": actuals[i],
                                    "pred_lane": round(float(preds[i]), 2),
                                    "pred_dow": np.nan, "pred_exp": np.nan, "pred_gbt": np.nan})
                continue

            # Lane 2 — Periodic
            if lane == "periodic":
                preds = predict_periodic(train, num_test)
                for i, d in enumerate(test_dates):
                    results.append({**base, "date": d, "actual": actuals[i],
                                    "pred_lane": round(float(preds[i]), 2),
                                    "pred_dow": np.nan, "pred_exp": np.nan, "pred_gbt": np.nan})
                continue

            # Lane 1 — Daily: DOW + ExpSmoothing + GBT (same as production)
            dow_model = DayOfWeekModel()
            exp_model = ExpSmoothingModel()
            dow_model.fit(train[["date", "qty"]])
            exp_model.fit(train[["date", "qty"]])

            dow_preds = dow_model.predict(test_dates)
            exp_preds = exp_model.predict(test_dates)

            # GBT: build feature rows from training data, predict test period
            future_feats = build_future_features(train, store, product, test_dates)
            if future_feats is not None and gbt.is_fitted:
                gbt_preds = gbt.predict(future_feats)
            else:
                gbt_preds = np.zeros(num_test)

            for i, d in enumerate(test_dates):
                results.append({
                    **base, "date": d, "actual": actuals[i],
                    "pred_lane": np.nan,   # filled by generate_accuracy_report
                    "pred_dow": round(dow_preds[i], 1),
                    "pred_exp": round(exp_preds[i], 1),
                    "pred_gbt": round(float(gbt_preds[i]), 1),
                })

    return pd.DataFrame(results)


def evaluate_models(backtest_results: pd.DataFrame) -> dict:
    """
    Evaluate DOW, ExpSmoothing, and GBT on daily-lane products and return
    optimal ensemble weights.

    Uses FORECAST_CONFIG["ensemble_weight_metric"] (default "mae") to score
    models. Weights are inverse-error: lower error → higher weight.
    GBT is scored from actual backtest predictions — no heuristic boost.
    """
    if backtest_results.empty:
        return {"dow": 0.33, "exp": 0.34, "gbt": 0.33}

    daily = backtest_results[backtest_results["lane"] == "daily"].dropna(
        subset=["pred_dow", "pred_exp"]
    )
    if daily.empty:
        return {"dow": 0.33, "exp": 0.34, "gbt": 0.33}

    metric_key = FORECAST_CONFIG.get("ensemble_weight_metric", "mae")

    model_cols = {"dow": "pred_dow", "exp": "pred_exp"}
    # Only include GBT if it was actually backtested (non-NaN predictions exist)
    if "pred_gbt" in daily.columns and daily["pred_gbt"].notna().any():
        model_cols["gbt"] = "pred_gbt"

    weights = {}
    for name, col in model_cols.items():
        valid = daily.dropna(subset=[col])
        if valid.empty:
            weights[name] = 0.0
            continue
        metrics = compute_metrics(valid["actual"].values, valid[col].values)
        err = metrics.get(metric_key, 100)
        # Guard against zero/near-zero error (perfect model) — use small floor
        weights[name] = 1.0 / max(err, 1e-3)

    # If GBT wasn't backtested, give it a modest default weight
    if "gbt" not in weights:
        weights["gbt"] = max(weights.values()) * 1.1

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
    - Lane 1 (Daily): DOW / ExpSmoothing / GBT / Ensemble breakdown + weights
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
        gw = weights.get("gbt", 0.33)
        total_w = dw + ew + gw
        has_gbt = "pred_gbt" in br.columns and br.loc[daily_mask, "pred_gbt"].notna().any()
        if has_gbt:
            br.loc[daily_mask, "pred_lane"] = (
                dw * br.loc[daily_mask, "pred_dow"] +
                ew * br.loc[daily_mask, "pred_exp"] +
                gw * br.loc[daily_mask, "pred_gbt"].fillna(0)
            ) / total_w
        else:
            de_total = dw + ew
            br.loc[daily_mask, "pred_lane"] = (
                dw * br.loc[daily_mask, "pred_dow"] +
                ew * br.loc[daily_mask, "pred_exp"]
            ) / de_total

    # Lane distribution (unique store-product pairs per lane)
    dist_parts = []
    for lane_name in ["daily", "periodic", "intermittent", "dormant"]:
        n = br[br["lane"] == lane_name].groupby(["store", "product"]).ngroups
        if n > 0:
            dist_parts.append(f"{n} {lane_name}")
    lines.append(f"\n  Lane distribution: {', '.join(dist_parts)}")

    metric_key = FORECAST_CONFIG.get("ensemble_weight_metric", "mae")
    lines.append(f"  Weight optimization metric: {metric_key.upper()}")

    # ── Lane 1: Daily ────────────────────────────────────────────────
    daily_br = br[daily_mask]
    if not daily_br.empty:
        lines.append(f"\n{'-' * 70}")
        n_daily = daily_br.groupby(["store", "product"]).ngroups
        lines.append(f"  Lane 1 — Daily ML ({n_daily} products):")
        model_cols = [("dow", "Day-of-Week"), ("exp", "Exp Smoothing"), ("gbt", "GBT")]
        for model_name, label in model_cols:
            pred_col = f"pred_{model_name}"
            if pred_col not in daily_br.columns:
                continue
            valid = daily_br.dropna(subset=[pred_col])
            if not valid.empty:
                m = compute_metrics(valid["actual"].values, valid[pred_col].values)
                lines.append(f"    {label:<16} MAE={m['mae']}  WMAPE={m['wmape']}%  "
                              f"Bias={m['bias']:+.2f}  Within1={m['accuracy_within_1']}%")

        ens_m = compute_metrics(daily_br["actual"].values, daily_br["pred_lane"].values)
        lines.append(f"    {'Ensemble':<16} MAE={ens_m['mae']}  WMAPE={ens_m['wmape']}%  "
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
    return "\n".join(lines)
