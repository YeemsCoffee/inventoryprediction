"""
Forecasting models.
Multiple approaches that get ensembled for robust predictions.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from config.products import FORECAST_CONFIG
import warnings

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Model 1: Enhanced Day-of-Week (improved version of original)
# ---------------------------------------------------------------------------

class DayOfWeekModel:
    """
    Day-of-week seasonal model with trend adjustment.
    Improved: uses weighted recent history, per-product trend.
    """

    def __init__(self, recent_days=21, decay_rate=0.95):
        self.recent_days = recent_days
        self.decay_rate = decay_rate
        self.dow_avg = {}
        self.trend = 1.0

    def fit(self, series: pd.DataFrame):
        """Fit on a single store-product series (columns: date, qty)."""
        s = series.sort_values("date").copy()
        if s["qty"].sum() == 0:
            self.dow_avg = {i: 0.0 for i in range(7)}
            return self

        # Weighted day-of-week averages (more recent = higher weight)
        s["dow"] = s["date"].dt.dayofweek
        s["days_ago"] = (s["date"].max() - s["date"]).dt.days
        s["weight"] = self.decay_rate ** s["days_ago"]

        for dow in range(7):
            mask = s["dow"] == dow
            if mask.sum() > 0:
                self.dow_avg[dow] = np.average(s.loc[mask, "qty"], weights=s.loc[mask, "weight"])
            else:
                self.dow_avg[dow] = 0.0

        # Trend: recent vs overall
        recent = s[s["days_ago"] <= self.recent_days]
        if len(recent) > 0 and s["qty"].mean() > 0:
            self.trend = recent["qty"].mean() / s["qty"].mean()
            self.trend = np.clip(self.trend, 0.3, 3.0)

        return self

    def predict(self, dates: pd.DatetimeIndex) -> np.ndarray:
        preds = []
        for d in dates:
            dow = d.dayofweek
            preds.append(max(0, self.dow_avg.get(dow, 0.0) * self.trend))
        return np.array(preds)


# ---------------------------------------------------------------------------
# Model 2: Exponential Smoothing (Holt-Winters)
# ---------------------------------------------------------------------------

class ExpSmoothingModel:
    """
    Holt-Winters exponential smoothing with weekly seasonality.
    Falls back to simple exponential smoothing for short series.
    """

    def __init__(self):
        self.model_fit = None
        self.fallback_value = 0.0

    def fit(self, series: pd.DataFrame):
        s = series.sort_values("date").set_index("date")["qty"]

        if len(s) < 14 or s.sum() == 0:
            self.fallback_value = s.mean() if len(s) > 0 else 0.0
            return self

        try:
            # Try Holt-Winters with weekly seasonality
            if len(s) >= 14:
                model = ExponentialSmoothing(
                    s.values,
                    trend="add",
                    seasonal="add",
                    seasonal_periods=7,
                    initialization_method="estimated",
                )
                self.model_fit = model.fit(optimized=True, use_brute=False)
            else:
                raise ValueError("too short")
        except Exception:
            try:
                # Fallback: simple exponential smoothing
                model = ExponentialSmoothing(
                    s.values,
                    trend="add",
                    initialization_method="estimated",
                )
                self.model_fit = model.fit(optimized=True)
            except Exception:
                self.fallback_value = s.tail(7).mean()

        return self

    def predict(self, dates: pd.DatetimeIndex) -> np.ndarray:
        n = len(dates)
        if self.model_fit is not None:
            try:
                preds = self.model_fit.forecast(n)
                return np.maximum(0, preds)
            except Exception:
                pass
        return np.full(n, max(0, self.fallback_value))


# ---------------------------------------------------------------------------
# Model 3: Gradient Boosted Trees
# ---------------------------------------------------------------------------

class GBTModel:
    """
    Gradient Boosted Tree model using engineered features.
    Captures non-linear relationships between features and demand.
    """

    FEATURE_COLS = [
        "dow", "day_of_month", "is_weekend", "is_monday", "is_friday",
        "dow_sin", "dow_cos", "dom_sin", "dom_cos",
        "lag_1", "lag_7", "lag_14",
        "rolling_mean_7", "rolling_mean_14", "rolling_mean_28",
        "rolling_std_7", "rolling_std_14",
        "rolling_max_7",
        "trend_7_28",
        "days_since_last_order",
        "product_hist_avg", "product_cv", "order_frequency",
    ]

    def __init__(self):
        self.model = GradientBoostingRegressor(
            loss=FORECAST_CONFIG["gbt_loss"],
            alpha=FORECAST_CONFIG["gbt_huber_alpha"],
            n_estimators=FORECAST_CONFIG["gbt_n_estimators"],
            max_depth=FORECAST_CONFIG["gbt_max_depth"],
            learning_rate=FORECAST_CONFIG["gbt_learning_rate"],
            subsample=FORECAST_CONFIG["gbt_subsample"],
            min_samples_leaf=FORECAST_CONFIG["gbt_min_samples_leaf"],
            random_state=42,
        )
        self.is_fitted = False

    def fit(self, feature_df: pd.DataFrame):
        """Fit on the full feature matrix (all store-products together)."""
        df = feature_df.dropna(subset=self.FEATURE_COLS).copy()
        if len(df) < 20:
            return self

        X = df[self.FEATURE_COLS].values
        y = df["qty"].values

        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, feature_df: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            return np.zeros(len(feature_df))

        X = feature_df[self.FEATURE_COLS].fillna(0).values
        preds = self.model.predict(X)
        return np.maximum(0, preds)

    def feature_importance(self) -> dict:
        if not self.is_fitted:
            return {}
        return dict(zip(self.FEATURE_COLS, self.model.feature_importances_))


# ---------------------------------------------------------------------------
# Ensemble
# ---------------------------------------------------------------------------

class EnsembleForecaster:
    """
    Combines multiple models with learned weights.
    Weights are determined by backtesting performance.
    """

    def __init__(self):
        self.dow_model = DayOfWeekModel()
        self.exp_model = ExpSmoothingModel()
        self.gbt_model = GBTModel()
        # Default weights — get updated by backtesting
        self.weights = {"dow": 0.25, "exp": 0.35, "gbt": 0.40}

    def set_weights(self, weights: dict):
        total = sum(weights.values())
        self.weights = {k: v / total for k, v in weights.items()}

    def fit(self, daily_demand: pd.DataFrame, feature_df: pd.DataFrame,
            store: str, product: str):
        """Fit all sub-models for a single store-product."""
        sp_demand = daily_demand[
            (daily_demand["store"] == store) & (daily_demand["product"] == product)
        ][["date", "qty"]]

        self.dow_model.fit(sp_demand)
        self.exp_model.fit(sp_demand)
        # GBT is trained globally, not per store-product

    def predict(self, dates: pd.DatetimeIndex, gbt_preds: np.ndarray = None) -> np.ndarray:
        dow_preds = self.dow_model.predict(dates)
        exp_preds = self.exp_model.predict(dates)

        if gbt_preds is None:
            gbt_preds = np.zeros(len(dates))

        ensemble = (
            self.weights["dow"] * dow_preds +
            self.weights["exp"] * exp_preds +
            self.weights["gbt"] * gbt_preds
        )
        return np.maximum(0, ensemble)
