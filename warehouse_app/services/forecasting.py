"""
Demand forecasting service.

Pure demand forecasting logic — calculates average daily orders and confidence.
Does NOT handle replenishment calculations (par levels, rounding, min-send).
That responsibility belongs to the replenishment service.

Uses actual store orders (ActualOrder) as the primary data source.
Falls back to daily usage (DailyUsage) if no actual order data exists.

Supported forecast methods:
    historical_simple_v1   — Unweighted average over order window (V1 default)
    historical_weighted_v1 — Exponential recency decay with optional DOW weighting
"""
from datetime import timedelta
from decimal import Decimal

from flask import current_app
from sqlalchemy import func

from warehouse_app.extensions import db
from warehouse_app.models.actual_order import ActualOrder
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot
from warehouse_app.models.store_item_setting import StoreItemSetting

VALID_FORECAST_METHODS = ('historical_simple_v1', 'historical_weighted_v1')


def _to_decimal(val):
    """Safely convert to Decimal."""
    if val is None:
        return Decimal('0')
    return Decimal(str(val))


# ── Data access helpers ──────────────────────────────────────────────

def get_average_orders(store_id, item_id, plan_date, days):
    """
    Return simple arithmetic average daily orders over the window.
    Uses ActualOrder as primary source, falls back to DailyUsage.

    Returns:
        (avg_orders: Decimal, record_count: int, source: str)
    """
    start_date = plan_date - timedelta(days=days)
    end_date = plan_date - timedelta(days=1)

    # Try actual orders first
    result = db.session.query(
        func.avg(ActualOrder.quantity_ordered),
        func.count(ActualOrder.id),
    ).filter(
        ActualOrder.store_id == store_id,
        ActualOrder.item_id == item_id,
        ActualOrder.order_date >= start_date,
        ActualOrder.order_date <= end_date,
    ).one()

    if result[1] > 0:
        return _to_decimal(result[0]), result[1], 'actual_orders'

    # Fall back to daily usage
    result = db.session.query(
        func.avg(DailyUsage.quantity_used),
        func.count(DailyUsage.id),
    ).filter(
        DailyUsage.store_id == store_id,
        DailyUsage.item_id == item_id,
        DailyUsage.usage_date >= start_date,
        DailyUsage.usage_date <= end_date,
    ).one()

    return _to_decimal(result[0]), result[1], 'daily_usage'


# Keep legacy function for backward compatibility with tests
def get_average_usage(store_id, item_id, plan_date, days):
    """
    Return simple arithmetic average daily usage over the window.
    Legacy function — delegates to get_average_orders.

    Returns:
        (avg_usage: Decimal, record_count: int)
    """
    avg, count, _source = get_average_orders(store_id, item_id, plan_date, days)
    return avg, count


def get_weighted_average_orders(store_id, item_id, plan_date, days,
                                decay_factor, dow_multiplier=0.0):
    """
    Return exponentially-weighted average daily orders.
    Uses ActualOrder as primary source, falls back to DailyUsage.

    Returns:
        (weighted_avg: Decimal, record_count: int, dow_matches: int, source: str)
    """
    start_date = plan_date - timedelta(days=days)
    end_date = plan_date - timedelta(days=1)
    plan_weekday = plan_date.weekday()

    # Try actual orders first
    rows = ActualOrder.query.filter(
        ActualOrder.store_id == store_id,
        ActualOrder.item_id == item_id,
        ActualOrder.order_date >= start_date,
        ActualOrder.order_date <= end_date,
    ).all()

    source = 'actual_orders'
    if not rows:
        # Fall back to daily usage
        usage_rows = DailyUsage.query.filter(
            DailyUsage.store_id == store_id,
            DailyUsage.item_id == item_id,
            DailyUsage.usage_date >= start_date,
            DailyUsage.usage_date <= end_date,
        ).all()
        # Convert to a common interface
        rows = []
        for u in usage_rows:
            rows.append(type('Row', (), {
                'quantity_ordered': u.quantity_used,
                'order_date': u.usage_date,
            })())
        source = 'daily_usage'

    if not rows:
        return Decimal('0'), 0, 0, source

    total_weighted = Decimal('0')
    total_weight = Decimal('0')
    dow_matches = 0
    decay = Decimal(str(decay_factor))

    for row in rows:
        row_date = row.order_date
        days_ago = (plan_date - row_date).days
        recency_weight = decay ** (days_ago - 1)

        dow_weight = Decimal('1')
        if dow_multiplier > 0 and row_date.weekday() == plan_weekday:
            dow_weight = Decimal('1') + Decimal(str(dow_multiplier))
            dow_matches += 1

        weight = recency_weight * dow_weight
        total_weighted += _to_decimal(row.quantity_ordered) * weight
        total_weight += weight

    if total_weight == 0:
        return Decimal('0'), len(rows), dow_matches, source

    weighted_avg = total_weighted / total_weight
    return weighted_avg, len(rows), dow_matches, source


# Keep legacy function for backward compatibility with tests
def get_weighted_average_usage(store_id, item_id, plan_date, days,
                               decay_factor, dow_multiplier=0.0):
    """
    Legacy function — delegates to get_weighted_average_orders.

    Returns:
        (weighted_avg: Decimal, record_count: int, dow_matches: int)
    """
    avg, count, dow, _source = get_weighted_average_orders(
        store_id, item_id, plan_date, days, decay_factor, dow_multiplier)
    return avg, count, dow


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


# ── Confidence & on-hand assessment (shared) ─────────────────────────

def _assess_on_hand(store_id, item_id, plan_date, confidence, explanations, warnings):
    """Assess on-hand inventory. Returns (on_hand, on_hand_date, confidence)."""
    on_hand, on_hand_date = get_latest_on_hand(store_id, item_id, plan_date)

    if on_hand is None:
        warnings.append('missing_snapshot')
        explanations.append('No inventory snapshot found \u2014 assuming 0 on hand')
        if confidence == 'high':
            confidence = 'medium'
    else:
        explanations.append(f'On-hand: {on_hand} (as of {on_hand_date})')

    return on_hand, on_hand_date, confidence


def _compute_coverage(record_count, window_days):
    """Return data coverage ratio (0.0 to 1.0)."""
    if window_days <= 0:
        return 0.0
    return min(record_count / window_days, 1.0)


# ── Simple forecast builder ──────────────────────────────────────────

def _build_simple_forecast(store_id, item_id, plan_date,
                           window_short, window_long, min_data_points):
    """
    Build a forecast using unweighted simple averages.
    Uses actual orders as primary data, falls back to daily usage.

    Returns the standard forecast dict.
    """
    forecast_method = 'historical_simple_v1'
    explanations = []
    warnings = []

    avg_short, count_short, source_short = get_average_orders(
        store_id, item_id, plan_date, window_short)
    avg_long, count_long, source_long = get_average_orders(
        store_id, item_id, plan_date, window_long)

    data_source = source_short or source_long

    if count_short >= min_data_points:
        avg_daily_usage = avg_short
        window_used = window_short
        data_points = count_short
        data_source = source_short
        source_label = 'actual orders' if source_short == 'actual_orders' else 'usage history'
        explanations.append(f'Based on {window_short}-day average {source_label}')
        confidence = 'high'
    elif count_long >= min_data_points:
        avg_daily_usage = avg_long
        window_used = window_long
        data_points = count_long
        data_source = source_long
        source_label = 'actual orders' if source_long == 'actual_orders' else 'usage history'
        explanations.append(
            f'Based on {window_long}-day average {source_label} '
            f'(insufficient {window_short}-day data)')
        confidence = 'medium'
    elif count_short > 0 or count_long > 0:
        if count_long > count_short:
            avg_daily_usage = avg_long
            window_used = window_long
            data_points = count_long
            data_source = source_long
        else:
            avg_daily_usage = avg_short
            window_used = window_short
            data_points = count_short
            data_source = source_short
        explanations.append('Limited order history available')
        confidence = 'low'
        warnings.append('sparse_usage_history')
    else:
        avg_daily_usage = Decimal('0')
        window_used = 0
        data_points = 0
        data_source = 'none'
        explanations.append('No order history available')
        confidence = 'low'
        warnings.append('sparse_usage_history')

    if data_source == 'daily_usage' and data_points > 0:
        explanations.append('Using usage history (no actual orders found)')

    if confidence == 'low':
        warnings.append('low_confidence')

    coverage = _compute_coverage(data_points, window_used)

    on_hand, on_hand_date, confidence = _assess_on_hand(
        store_id, item_id, plan_date, confidence, explanations, warnings)

    return {
        'avg_daily_usage': avg_daily_usage,
        'confidence': confidence,
        'window_days': window_used,
        'data_points': data_points,
        'data_coverage': coverage,
        'data_source': data_source,
        'on_hand': on_hand,
        'on_hand_date': on_hand_date,
        'explanations': explanations,
        'warnings': warnings,
        'forecast_method': forecast_method,
    }


# ── Weighted forecast builder ────────────────────────────────────────

def _build_weighted_forecast(store_id, item_id, plan_date,
                             window_short, window_long, min_data_points,
                             decay_factor, dow_multiplier):
    """
    Build a forecast using exponential recency decay and optional DOW weighting.
    Uses actual orders as primary data, falls back to daily usage.

    Returns the standard forecast dict.
    """
    forecast_method = 'historical_weighted_v1'
    explanations = []
    warnings = []
    dow_enabled = dow_multiplier > 0

    # Short window
    avg_short, count_short, dow_short, source_short = get_weighted_average_orders(
        store_id, item_id, plan_date, window_short, decay_factor, dow_multiplier)

    # Long window
    avg_long, count_long, dow_long, source_long = get_weighted_average_orders(
        store_id, item_id, plan_date, window_long, decay_factor, dow_multiplier)

    data_source = source_short or source_long

    # ── Select best window ───────────────────────────────────
    if count_short >= min_data_points:
        avg_daily_usage = avg_short
        window_used = window_short
        data_points = count_short
        dow_matches = dow_short
        data_source = source_short
        source_label = 'orders' if source_short == 'actual_orders' else 'usage'
        explanations.append(
            f'Weighted {window_short}-day avg {source_label} (decay={decay_factor})')
        confidence = 'high'
    elif count_long >= min_data_points:
        avg_daily_usage = avg_long
        window_used = window_long
        data_points = count_long
        dow_matches = dow_long
        data_source = source_long
        source_label = 'orders' if source_long == 'actual_orders' else 'usage'
        explanations.append(
            f'Weighted {window_long}-day avg {source_label} (decay={decay_factor}, '
            f'insufficient {window_short}-day data)')
        confidence = 'medium'
    elif count_short > 0 or count_long > 0:
        if count_long > count_short:
            avg_daily_usage = avg_long
            window_used = window_long
            data_points = count_long
            dow_matches = dow_long
            data_source = source_long
        else:
            avg_daily_usage = avg_short
            window_used = window_short
            data_points = count_short
            dow_matches = dow_short
            data_source = source_short
        explanations.append('Limited order history available (weighted)')
        confidence = 'low'
        warnings.append('sparse_usage_history')
    else:
        avg_daily_usage = Decimal('0')
        window_used = 0
        data_points = 0
        dow_matches = 0
        data_source = 'none'
        explanations.append('No order history available')
        confidence = 'low'
        warnings.append('sparse_usage_history')

    if data_source == 'daily_usage' and data_points > 0:
        explanations.append('Using usage history (no actual orders found)')

    # ── Data coverage assessment ─────────────────────────────
    coverage = _compute_coverage(data_points, window_used)

    if 0 < coverage < 0.5 and confidence == 'high':
        confidence = 'medium'
        warnings.append('low_data_coverage')
        explanations.append(
            f'Data coverage {coverage:.0%} of {window_used}-day window')

    # ── DOW awareness ────────────────────────────────────────
    if dow_enabled:
        explanations.append(f'DOW weighting x{1 + dow_multiplier:.1f} applied')
        if window_used > 0:
            expected_dow_days = max(1, window_used // 7)
            if dow_matches < expected_dow_days and confidence == 'high':
                confidence = 'medium'
                warnings.append('sparse_dow_history')
                explanations.append(
                    f'Only {dow_matches} same-weekday data point(s) '
                    f'in {window_used}-day window')

    if confidence == 'low':
        warnings.append('low_confidence')

    on_hand, on_hand_date, confidence = _assess_on_hand(
        store_id, item_id, plan_date, confidence, explanations, warnings)

    return {
        'avg_daily_usage': avg_daily_usage,
        'confidence': confidence,
        'window_days': window_used,
        'data_points': data_points,
        'data_coverage': coverage,
        'data_source': data_source,
        'dow_matches': dow_matches,
        'on_hand': on_hand,
        'on_hand_date': on_hand_date,
        'explanations': explanations,
        'warnings': warnings,
        'forecast_method': forecast_method,
    }


# ── Public dispatch ──────────────────────────────────────────────────

def build_forecast(store_id, item_id, plan_date):
    """
    Build a demand forecast for one store-item pair.

    Uses actual store orders as the primary data source. If no actual order
    data exists, falls back to daily usage history.

    Dispatches to the appropriate forecast builder based on FORECAST_METHOD config.

    Returns a dict with:
        avg_daily_usage: Decimal - forecasted daily demand
        confidence: str - 'high', 'medium', or 'low'
        window_days: int - the usage window that was used
        data_points: int - number of data points in the chosen window
        data_coverage: float - fraction of window days with data (0.0-1.0)
        data_source: str - 'actual_orders', 'daily_usage', or 'none'
        on_hand: Decimal | None - latest on-hand quantity
        on_hand_date: date | None - date of the latest snapshot
        explanations: list[str] - human-readable explanation steps
        warnings: list[str] - warning flags
        forecast_method: str - versioned method name
    """
    forecast_method = current_app.config.get('FORECAST_METHOD', 'historical_simple_v1')
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

    if forecast_method == 'historical_weighted_v1':
        decay_factor = current_app.config.get('WEIGHTED_DECAY_FACTOR', 0.9)
        dow_multiplier = current_app.config.get('WEIGHTED_DOW_MULTIPLIER', 0.0)
        return _build_weighted_forecast(
            store_id, item_id, plan_date,
            window_short, window_long, min_data_points,
            decay_factor, dow_multiplier,
        )

    # Default: historical_simple_v1
    return _build_simple_forecast(
        store_id, item_id, plan_date,
        window_short, window_long, min_data_points,
    )
