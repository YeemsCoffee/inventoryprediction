"""
Demand forecasting service.

Pure demand forecasting logic — calculates average daily usage and confidence.
Does NOT handle replenishment calculations (par levels, rounding, min-send).
That responsibility belongs to the replenishment service.
"""
from datetime import timedelta
from decimal import Decimal

from flask import current_app
from sqlalchemy import func

from warehouse_app.extensions import db
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot
from warehouse_app.models.store_item_setting import StoreItemSetting


def _to_decimal(val):
    """Safely convert to Decimal."""
    if val is None:
        return Decimal('0')
    return Decimal(str(val))


def get_average_usage(store_id, item_id, plan_date, days):
    """
    Return average daily usage over the given window ending the day before plan_date.

    Returns:
        (avg_usage: Decimal, record_count: int)
    """
    start_date = plan_date - timedelta(days=days)
    end_date = plan_date - timedelta(days=1)

    result = db.session.query(
        func.avg(DailyUsage.quantity_used),
        func.count(DailyUsage.id),
    ).filter(
        DailyUsage.store_id == store_id,
        DailyUsage.item_id == item_id,
        DailyUsage.usage_date >= start_date,
        DailyUsage.usage_date <= end_date,
    ).one()

    avg_usage = result[0]
    record_count = result[1]
    return _to_decimal(avg_usage), record_count


def get_latest_on_hand(store_id, item_id, plan_date):
    """
    Return the latest inventory snapshot quantity on or before plan_date.

    Returns:
        (quantity: Decimal | None, snapshot_date: date | None)
    """
    snapshot = InventorySnapshot.query.filter(
        InventorySnapshot.store_id == store_id,
        InventorySnapshot.item_id == item_id,
        InventorySnapshot.snapshot_date <= plan_date,
    ).order_by(InventorySnapshot.snapshot_date.desc()).first()

    if snapshot is None:
        return None, None
    return _to_decimal(snapshot.quantity_on_hand), snapshot.snapshot_date


def build_forecast(store_id, item_id, plan_date):
    """
    Build a demand forecast for one store-item pair.

    Uses configurable short/long usage windows and per-setting overrides.

    Returns a dict with:
        avg_daily_usage: Decimal - forecasted daily demand
        confidence: str - 'high', 'medium', or 'low'
        window_days: int - the usage window that was used
        data_points: int - number of data points in the chosen window
        on_hand: Decimal | None - latest on-hand quantity (None if no snapshot)
        on_hand_date: date | None - date of the latest snapshot
        explanations: list[str] - human-readable explanation steps
        warnings: list[str] - warning flags
    """
    # Read config values
    window_short = current_app.config.get('DEFAULT_USAGE_WINDOW_SHORT', 7)
    window_long = current_app.config.get('DEFAULT_USAGE_WINDOW_LONG', 14)
    min_data_points = current_app.config.get('MIN_DATA_POINTS_HIGH_CONFIDENCE', 5)

    # Per-setting override for usage window
    setting = StoreItemSetting.query.filter_by(
        store_id=store_id, item_id=item_id, active=True,
    ).first()
    if setting and setting.usage_window_days:
        window_short = setting.usage_window_days
        window_long = max(window_short * 2, window_long)

    explanations = []
    warnings = []
    confidence = 'high'

    # ── Calculate usage averages ────────────────────────────
    avg_short, count_short = get_average_usage(store_id, item_id, plan_date, window_short)
    avg_long, count_long = get_average_usage(store_id, item_id, plan_date, window_long)

    if count_short >= min_data_points:
        avg_daily_usage = avg_short
        window_used = window_short
        data_points = count_short
        explanations.append(f'Based on {window_short}-day average usage')
        confidence = 'high'
    elif count_long >= min_data_points:
        avg_daily_usage = avg_long
        window_used = window_long
        data_points = count_long
        explanations.append(f'Based on {window_long}-day average usage (insufficient {window_short}-day data)')
        confidence = 'medium'
    elif count_short > 0 or count_long > 0:
        if count_long > count_short:
            avg_daily_usage = avg_long
            window_used = window_long
            data_points = count_long
        else:
            avg_daily_usage = avg_short
            window_used = window_short
            data_points = count_short
        explanations.append('Limited usage history available')
        confidence = 'low'
        warnings.append('sparse_usage_history')
    else:
        avg_daily_usage = Decimal('0')
        window_used = 0
        data_points = 0
        explanations.append('No usage history available')
        confidence = 'low'
        warnings.append('sparse_usage_history')

    if confidence == 'low':
        warnings.append('low_confidence')

    # ── Get current on-hand inventory ───────────────────────
    on_hand, on_hand_date = get_latest_on_hand(store_id, item_id, plan_date)

    if on_hand is None:
        warnings.append('missing_snapshot')
        explanations.append('No inventory snapshot found — assuming 0 on hand')
        if confidence == 'high':
            confidence = 'medium'
    else:
        explanations.append(f'On-hand: {on_hand} (as of {on_hand_date})')

    return {
        'avg_daily_usage': avg_daily_usage,
        'confidence': confidence,
        'window_days': window_used,
        'data_points': data_points,
        'on_hand': on_hand,
        'on_hand_date': on_hand_date,
        'explanations': explanations,
        'warnings': warnings,
    }
