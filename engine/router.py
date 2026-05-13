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

# Days of demand history used to compute routing signals.
# Kept separate from the forecast window so lane assignment stays stable.
ROUTING_WINDOW = 28


def classify_lane(product: str, sp_demand: pd.DataFrame) -> str:
    """
    Route a product to its forecast lane.

    Priority:
    1. Explicit override in PRODUCT_LANES (config/products.py) — always wins.
    2. Dynamic classification from the most recent ROUTING_WINDOW days:
       - zero-rate >= 95%  → dormant   (Lane 4)
       - zero-rate >= 65%  → intermittent (Lane 3)
       - in PERIODIC_PRODUCTS → periodic (Lane 2)
       - otherwise         → daily ML ensemble (Lane 1)

    sp_demand: daily demand DataFrame (columns: date, qty).
               Pass training-data-only slice during backtesting to avoid
               look-ahead bias in lane classification.

    Returns: 'daily' | 'periodic' | 'intermittent' | 'dormant'
    """
    if product in PRODUCT_LANES:
        return PRODUCT_LANES[product]

    recent = sp_demand.tail(ROUTING_WINDOW)
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

    Separates order probability from order size so that zero-order days
    do not suppress the forecast the way a plain average would.

    sp_demand: demand history (training data only when backtesting).
    """
    recent = sp_demand.tail(ROUTING_WINDOW)
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
    recent = sp_demand.tail(ROUTING_WINDOW)
    nonzero = recent[recent["qty"] > 0]["qty"]
    if len(nonzero) == 0:
        return np.zeros(num_days)
    avg_interval = len(recent) / len(nonzero)
    effective_interval = max(avg_interval, float(delivery_window))
    expected_daily = nonzero.mean() / effective_interval
    return np.full(num_days, max(0.0, expected_daily))
