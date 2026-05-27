"""
Forecast lane routing.

Classifies a store-product demand series into one of four forecast lanes
and produces lane-specific point predictions.

Imported by both run_forecast.py (production forecasting) and
engine/backtest.py (backtesting), so production and evaluation always
use identical routing logic.
"""

import numpy as np
import pandas as pd
from config.products import PRODUCT_LANES, PERIODIC_PRODUCTS

# Primary routing window — used for lane classification and intermittent prediction.
# Kept separate from the forecast window so lane assignment stays stable.
ROUTING_WINDOW = 28

# Minimum order days required for a reliable frequency estimate.
# If the primary window has fewer, we extend to EXTENDED_WINDOWS in order.
MIN_ORDER_DAYS = 3
EXTENDED_WINDOWS = [60, 90]


def _get_demand_window(sp_demand: pd.DataFrame, min_orders: int = MIN_ORDER_DAYS) -> pd.DataFrame:
    """
    Return the shortest lookback window that contains at least min_orders order days.

    Tries ROUTING_WINDOW first (28d), then EXTENDED_WINDOWS (60d, 90d), then
    full history. Falls back to the 28-day slice if no orders exist at all.

    This prevents monthly items (e.g. Cafiza, Rinza) from being starved of
    signal when the 28-day window happens to have 0 orders.
    """
    for window in [ROUTING_WINDOW] + EXTENDED_WINDOWS + [len(sp_demand)]:
        recent = sp_demand.tail(window)
        if int((recent["qty"] > 0).sum()) >= min_orders:
            return recent
    # No orders in any window — return the standard slice for dormant detection
    return sp_demand.tail(ROUTING_WINDOW)


def classify_lane(product: str, sp_demand: pd.DataFrame) -> str:
    """
    Route a product to its forecast lane.

    Priority:
    1. Explicit override in PRODUCT_LANES (config/products.py) — always wins.
    2. Dynamic classification using an adaptive lookback window:
       - zero-rate >= 95%  → dormant      (Lane 4)
       - zero-rate >= 65%  → intermittent (Lane 3)
       - in PERIODIC_PRODUCTS → periodic  (Lane 2)
       - otherwise         → daily ML ensemble (Lane 1)

    The adaptive window extends to 60 or 90 days when the 28-day window has
    fewer than MIN_ORDER_DAYS orders, preventing monthly items from being
    misclassified as dormant due to an unlucky recent window.

    sp_demand: daily demand DataFrame (columns: date, qty).
               Pass training-data-only slice during backtesting to avoid
               look-ahead bias in lane classification.

    Returns: 'daily' | 'periodic' | 'intermittent' | 'dormant'
    """
    if product in PRODUCT_LANES:
        return PRODUCT_LANES[product]

    recent = _get_demand_window(sp_demand)
    n_days = len(recent)
    if n_days == 0 or recent["qty"].sum() == 0:
        return "dormant"

    n_order_days = int((recent["qty"] > 0).sum())
    zero_rate = 1.0 - (n_order_days / n_days)

    if zero_rate >= 0.95:
        return "dormant"
    if zero_rate >= 0.65:
        return "intermittent"
    if product in PERIODIC_PRODUCTS:
        return "periodic"
    return "daily"


def predict_intermittent(sp_demand: pd.DataFrame, num_days: int) -> np.ndarray:
    """
    Lane 3 — Intermittent: P(order) × E[qty | order] as a flat daily rate.

    Uses an adaptive lookback window (28 → 60 → 90 → full history) to ensure
    at least MIN_ORDER_DAYS data points, so monthly items get a stable
    frequency estimate rather than a noise-driven near-zero rate.

    sp_demand: demand history (training data only when backtesting).
    """
    recent = _get_demand_window(sp_demand)
    nonzero = recent[recent["qty"] > 0]["qty"]
    if len(nonzero) == 0:
        return np.zeros(num_days)
    order_freq = len(nonzero) / len(recent)
    expected_daily = order_freq * nonzero.mean()
    return np.full(num_days, max(0.0, expected_daily))


def predict_periodic(sp_demand: pd.DataFrame, num_days: int,
                     delivery_window: int = 3) -> np.ndarray:
    """
    Lane 2 — Periodic: avg_order_size / avg_inter_order_interval as a flat daily rate.

    Smooths the noisy daily ordering pattern for items (ice cups, lids, sleeves)
    that are replenished on a predictable 2–3 day cadence.
    The interval is floored at delivery_window to avoid over-smoothing.

    sp_demand: demand history (training data only when backtesting).
    """
    recent = _get_demand_window(sp_demand)
    nonzero = recent[recent["qty"] > 0]["qty"]
    if len(nonzero) == 0:
        return np.zeros(num_days)
    avg_interval = len(recent) / len(nonzero)
    effective_interval = max(avg_interval, float(delivery_window))
    expected_daily = nonzero.mean() / effective_interval
    return np.full(num_days, max(0.0, expected_daily))
