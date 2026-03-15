"""
Feature engineering pipeline.
Transforms raw daily demand into rich feature vectors for ML models.
"""

import numpy as np
import pandas as pd


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


def build_feature_matrix(daily_demand: pd.DataFrame) -> pd.DataFrame:
    """Full feature engineering pipeline."""
    df = daily_demand.copy()
    df = add_calendar_features(df)
    df = add_lag_features(df)
    df = add_trend_features(df)
    df = add_product_features(df)
    return df
