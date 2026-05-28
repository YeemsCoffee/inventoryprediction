"""
Feature engineering pipeline.
Transforms raw daily demand into rich feature vectors for ML models.
"""

import numpy as np
import pandas as pd
from config.products import FORECAST_CONFIG


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add time-based features from the date column."""
    df = df.copy()
    df["dow"] = df["date"].dt.dayofweek          # 0=Mon, 6=Sun
    df["day_of_month"] = df["date"].dt.day
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["month"] = df["date"].dt.month
    df["is_weekend"] = (df["dow"] >= 5).astype(int)
    df["is_monday"] = (df["dow"] == 0).astype(int)
    df["is_friday"] = (df["dow"] == 4).astype(int)

    # Cyclical encoding of day-of-week (captures that Sun and Mon are close)
    df["dow_sin"] = np.sin(2 * np.pi * df["dow"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dow"] / 7)

    # Cyclical encoding of day-of-month
    df["dom_sin"] = np.sin(2 * np.pi * df["day_of_month"] / 31)
    df["dom_cos"] = np.cos(2 * np.pi * df["day_of_month"] / 31)

    return df


def add_lag_features(df: pd.DataFrame, lags=(1, 7, 14)) -> pd.DataFrame:
    """Add lagged demand features per store-product."""
    df = df.sort_values(["store", "product", "date"]).copy()

    for lag in lags:
        df[f"lag_{lag}"] = df.groupby(["store", "product"])["qty"].shift(lag)

    # Rolling averages
    for window in (7, 14, 28):
        df[f"rolling_mean_{window}"] = (
            df.groupby(["store", "product"])["qty"]
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
        )
        df[f"rolling_std_{window}"] = (
            df.groupby(["store", "product"])["qty"]
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).std())
        )

    # Rolling max (captures spike patterns)
    df["rolling_max_7"] = (
        df.groupby(["store", "product"])["qty"]
        .transform(lambda x: x.shift(1).rolling(7, min_periods=1).max())
    )

    # Last nonzero order qty — carries forward the size of the most recent
    # actual order. Distinct from lag_1 (which is 0 on non-order days).
    # shift(1) prevents look-ahead — today's row sees up to yesterday only.
    df["last_order_qty"] = (
        df.groupby(["store", "product"])["qty"]
        .transform(lambda x: x.shift(1).replace(0, np.nan).ffill().fillna(0))
    )

    return df


def add_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add trend indicators comparing recent vs historical demand."""
    df = df.sort_values(["store", "product", "date"]).copy()

    # Short-term trend: 7-day avg / 28-day avg
    rm7 = df.groupby(["store", "product"])["qty"].transform(
        lambda x: x.shift(1).rolling(7, min_periods=1).mean()
    )
    rm28 = df.groupby(["store", "product"])["qty"].transform(
        lambda x: x.shift(1).rolling(28, min_periods=1).mean()
    )
    df["trend_7_28"] = (rm7 / rm28.replace(0, np.nan)).fillna(1.0).clip(0.2, 5.0)

    # Days since last order (captures sporadic ordering)
    def days_since_last(series):
        result = []
        last_order = None
        for i, (val, date) in enumerate(zip(series.values, series.index)):
            if last_order is not None:
                result.append((date - last_order).days)
            else:
                result.append(0)
            if val > 0:
                last_order = date
        return pd.Series(result, index=series.index)

    df["days_since_last_order"] = (
        df.set_index("date")
        .groupby(["store", "product"])["qty"]
        .transform(days_since_last)
        .values
    )

    return df


def add_product_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add product-level aggregate features."""
    df = df.copy()

    # Historical average daily demand per store-product
    hist_avg = df.groupby(["store", "product"])["qty"].transform("mean")
    df["product_hist_avg"] = hist_avg

    # Coefficient of variation (volatility measure)
    hist_std = df.groupby(["store", "product"])["qty"].transform("std").fillna(0)
    df["product_cv"] = (hist_std / hist_avg.replace(0, np.nan)).fillna(0).clip(0, 10)

    # Order frequency (what fraction of days have non-zero orders)
    df["order_frequency"] = df.groupby(["store", "product"])["qty"].transform(
        lambda x: (x > 0).mean()
    )

    return df


def classify_volume_tier(avg_demand: float) -> str:
    """Classify a store-product into a volume tier based on avg daily demand."""
    tiers = FORECAST_CONFIG["volume_tiers"]
    if avg_demand >= tiers["high"]["min_avg_demand"]:
        return "high"
    elif avg_demand >= tiers["low"]["min_avg_demand"]:
        return "low"
    else:
        return "sporadic"


def add_volume_tier(df: pd.DataFrame) -> pd.DataFrame:
    """Add volume_tier column based on per-store-product avg demand."""
    df = df.copy()
    avg_demand = df.groupby(["store", "product"])["qty"].transform("mean")
    df["volume_tier"] = avg_demand.apply(classify_volume_tier)
    return df


def get_tier_map(daily_demand: pd.DataFrame) -> dict:
    """Return {(store, product): tier} mapping for all items."""
    avg = daily_demand.groupby(["store", "product"])["qty"].mean()
    return {k: classify_volume_tier(v) for k, v in avg.items()}


def build_feature_matrix(daily_demand: pd.DataFrame) -> pd.DataFrame:
    """Full feature engineering pipeline."""
    df = daily_demand.copy()
    df = add_calendar_features(df)
    df = add_lag_features(df)
    df = add_trend_features(df)
    df = add_product_features(df)
    df = add_volume_tier(df)
    return df


def build_future_features(
    sp_demand: pd.DataFrame,
    store: str,
    product: str,
    forecast_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """
    Build GBT inference feature rows for future dates.

    Uses the tail of sp_demand (training data only) to compute lag/rolling
    stats, then projects them forward across forecast_dates.

    Note: lag and rolling features are frozen at the last training date and
    reused across the full horizon — this is a static approximation, not
    recursive forecasting. Adequate for near-term stability.

    Returns None if the product has zero historical demand.
    """
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
    last_order_qty = float(sp[sp["qty"] > 0]["qty"].iloc[-1]) if (sp["qty"] > 0).any() else 0.0

    for d in forecast_dates:
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
            "last_order_qty": last_order_qty,
            "trend_7_28": np.clip(trend, 0.2, 5.0),
            "days_since_last_order": (d - last_order_date).days if pd.notna(last_order_date) else 0,
            "product_hist_avg": hist_avg,
            "product_cv": np.clip(cv, 0, 10),
            "order_frequency": order_freq,
        }
        rows.append(row)

    return pd.DataFrame(rows)
