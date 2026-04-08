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
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.inventory_snapshot import InventorySnapshot
from warehouse_app.models.store_item_setting import StoreItemSetting

from config.products import PERIODIC_PRODUCTS, PRODUCT_LANES

VALID_FORECAST_METHODS = ('historical_simple_v1', 'historical_weighted_v1')


def _to_decimal(val):
    """Safely convert to Decimal."""
    if val is None:
        return Decimal('0')
    return Decimal(str(val))


# ── Data access helpers ──────────────────────────────────────────────

def get_average_orders(store_id, item_id, plan_date, days):
    """
    Return simple arithmetic average daily demand over the window.

    Merges actual orders with daily usage: for each date in the window,
    actual orders take priority. Daily usage fills in dates with no orders.

    Returns:
        (avg_demand: Decimal, record_count: int, source: str)
    """
    start_date = plan_date - timedelta(days=days)
    end_date = plan_date - timedelta(days=1)

    # Build a per-date quantity map: actual orders take priority
    demand_by_date = {}

    # Load daily usage first (lower priority)
    usage_rows = db.session.query(
        DailyUsage.usage_date, DailyUsage.quantity_used,
    ).filter(
        DailyUsage.store_id == store_id,
        DailyUsage.item_id == item_id,
        DailyUsage.usage_date >= start_date,
        DailyUsage.usage_date <= end_date,
    ).all()
    for row_date, qty in usage_rows:
        demand_by_date[row_date] = _to_decimal(qty)

    # Overlay actual orders (higher priority — overwrites usage for same date)
    order_rows = db.session.query(
        ActualOrder.order_date, ActualOrder.quantity_ordered,
    ).filter(
        ActualOrder.store_id == store_id,
        ActualOrder.item_id == item_id,
        ActualOrder.order_date >= start_date,
        ActualOrder.order_date <= end_date,
    ).all()
    has_orders = len(order_rows) > 0
    for row_date, qty in order_rows:
        demand_by_date[row_date] = _to_decimal(qty)

    if not demand_by_date:
        return Decimal('0'), 0, 'none'

    total = sum(demand_by_date.values())
    count = len(demand_by_date)
    avg = total / count

    source = 'blended' if has_orders and usage_rows else (
        'actual_orders' if has_orders else 'daily_usage')

    return avg, count, source


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
    Return exponentially-weighted average daily demand.

    Merges actual orders with daily usage: for each date in the window,
    actual orders take priority. Daily usage fills in dates with no orders.

    Returns:
        (weighted_avg: Decimal, record_count: int, dow_matches: int, source: str)
    """
    start_date = plan_date - timedelta(days=days)
    end_date = plan_date - timedelta(days=1)
    plan_weekday = plan_date.weekday()

    # Build a per-date quantity map: actual orders take priority
    demand_by_date = {}

    # Load daily usage first (lower priority)
    usage_rows = DailyUsage.query.filter(
        DailyUsage.store_id == store_id,
        DailyUsage.item_id == item_id,
        DailyUsage.usage_date >= start_date,
        DailyUsage.usage_date <= end_date,
    ).all()
    for u in usage_rows:
        demand_by_date[u.usage_date] = _to_decimal(u.quantity_used)

    # Overlay actual orders (higher priority)
    order_rows = ActualOrder.query.filter(
        ActualOrder.store_id == store_id,
        ActualOrder.item_id == item_id,
        ActualOrder.order_date >= start_date,
        ActualOrder.order_date <= end_date,
    ).all()
    has_orders = len(order_rows) > 0
    for o in order_rows:
        demand_by_date[o.order_date] = _to_decimal(o.quantity_ordered)

    if not demand_by_date:
        return Decimal('0'), 0, 0, 'none'

    source = 'blended' if has_orders and usage_rows else (
        'actual_orders' if has_orders else 'daily_usage')

    total_weighted = Decimal('0')
    total_weight = Decimal('0')
    dow_matches = 0
    decay = Decimal(str(decay_factor))

    for row_date, qty in demand_by_date.items():
        days_ago = (plan_date - row_date).days
        recency_weight = decay ** (days_ago - 1)

        dow_weight = Decimal('1')
        if dow_multiplier > 0 and row_date.weekday() == plan_weekday:
            dow_weight = Decimal('1') + Decimal(str(dow_multiplier))
            dow_matches += 1

        weight = recency_weight * dow_weight
        total_weighted += qty * weight
        total_weight += weight

    count = len(demand_by_date)
    if total_weight == 0:
        return Decimal('0'), count, dow_matches, source

    weighted_avg = total_weighted / total_weight
    return weighted_avg, count, dow_matches, source


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

def _assess_on_hand(store_id, item_id, plan_date, confidence, explanations,
                    warnings, avg_daily_usage=None):
    """Assess on-hand inventory, projecting forward if snapshot is stale.

    If the latest snapshot predates plan_date, the on-hand quantity is
    reduced by avg_daily_usage for each intervening day so that
    predictions for future dates reflect expected consumption.

    Returns (on_hand, on_hand_date, confidence).
    """
    on_hand, on_hand_date = get_latest_on_hand(store_id, item_id, plan_date)

    if on_hand is None:
        warnings.append('missing_snapshot')
        explanations.append('No inventory snapshot found \u2014 assuming 0 on hand')
        if confidence == 'high':
            confidence = 'medium'
    else:
        days_since = (plan_date - on_hand_date).days
        if days_since > 0 and avg_daily_usage and avg_daily_usage > 0:
            projected = on_hand - (avg_daily_usage * days_since)
            if projected < 0:
                projected = Decimal('0')
            explanations.append(
                f'On-hand: {on_hand} (as of {on_hand_date}), '
                f'projected to {projected} by {plan_date} '
                f'({days_since}d × {avg_daily_usage}/d)')
            on_hand = projected
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
        source_label = {'actual_orders': 'actual orders', 'blended': 'orders + usage', 'daily_usage': 'usage history'}.get(source_short, 'usage history')
        explanations.append(f'Based on {window_short}-day average {source_label}')
        confidence = 'high'
    elif count_long >= min_data_points:
        avg_daily_usage = avg_long
        window_used = window_long
        data_points = count_long
        data_source = source_long
        source_label = {'actual_orders': 'actual orders', 'blended': 'orders + usage', 'daily_usage': 'usage history'}.get(source_long, 'usage history')
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

    if confidence == 'low':
        warnings.append('low_confidence')

    coverage = _compute_coverage(data_points, window_used)

    on_hand, on_hand_date, confidence = _assess_on_hand(
        store_id, item_id, plan_date, confidence, explanations, warnings,
        avg_daily_usage=avg_daily_usage)

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
        source_label = {'actual_orders': 'orders', 'blended': 'orders+usage', 'daily_usage': 'usage'}.get(source_short, 'usage')
        explanations.append(
            f'Weighted {window_short}-day avg {source_label} (decay={decay_factor})')
        confidence = 'high'
    elif count_long >= min_data_points:
        avg_daily_usage = avg_long
        window_used = window_long
        data_points = count_long
        dow_matches = dow_long
        data_source = source_long
        source_label = {'actual_orders': 'orders', 'blended': 'orders+usage', 'daily_usage': 'usage'}.get(source_long, 'usage')
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
        store_id, item_id, plan_date, confidence, explanations, warnings,
        avg_daily_usage=avg_daily_usage)

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


# ── Lane routing helpers ─────────────────────────────────────────────

def _get_demand_stats(store_id, item_id, plan_date, window_days):
    """
    Compute demand statistics over a lookback window for lane classification.

    Uses the same ActualOrder-over-DailyUsage priority as get_average_orders.

    Returns a dict:
        zero_rate    — fraction of recorded days with zero demand (0.0–1.0)
        avg_demand   — mean daily demand including zeros
        avg_nonzero  — mean demand on order-days only
        cv           — coefficient of variation of non-zero quantities
        n_days       — total days with any record in the window
        n_order_days — days where quantity > 0
    """
    start_date = plan_date - timedelta(days=window_days)
    end_date = plan_date - timedelta(days=1)

    demand_by_date = {}

    usage_rows = db.session.query(
        DailyUsage.usage_date, DailyUsage.quantity_used,
    ).filter(
        DailyUsage.store_id == store_id,
        DailyUsage.item_id == item_id,
        DailyUsage.usage_date >= start_date,
        DailyUsage.usage_date <= end_date,
    ).all()
    for row_date, qty in usage_rows:
        demand_by_date[row_date] = float(qty or 0)

    order_rows = db.session.query(
        ActualOrder.order_date, ActualOrder.quantity_ordered,
    ).filter(
        ActualOrder.store_id == store_id,
        ActualOrder.item_id == item_id,
        ActualOrder.order_date >= start_date,
        ActualOrder.order_date <= end_date,
    ).all()
    for row_date, qty in order_rows:
        demand_by_date[row_date] = float(qty or 0)

    if not demand_by_date:
        return {
            'zero_rate': 1.0, 'avg_demand': 0.0, 'avg_nonzero': 0.0,
            'cv': 0.0, 'n_days': 0, 'n_order_days': 0,
        }

    qtys = list(demand_by_date.values())
    n_days = len(qtys)
    nonzero_qtys = [q for q in qtys if q > 0]
    n_order_days = len(nonzero_qtys)

    zero_rate = 1.0 - (n_order_days / n_days)
    avg_demand = sum(qtys) / n_days
    avg_nonzero = sum(nonzero_qtys) / n_order_days if n_order_days > 0 else 0.0

    if n_order_days > 1:
        mean = avg_nonzero
        variance = sum((q - mean) ** 2 for q in nonzero_qtys) / (n_order_days - 1)
        cv = (variance ** 0.5) / mean if mean > 0 else 0.0
    else:
        cv = 0.0

    return {
        'zero_rate': zero_rate,
        'avg_demand': avg_demand,
        'avg_nonzero': avg_nonzero,
        'cv': cv,
        'n_days': n_days,
        'n_order_days': n_order_days,
    }


def _classify_lane(item_name, stats, dormant_threshold, intermittent_threshold):
    """
    Determine the forecast lane for a product.

    Priority:
    1. Explicit override in PRODUCT_LANES — always wins.
    2. No demand data at all → dormant.
    3. Zero-rate >= dormant_threshold → dormant (Lane 4).
    4. Zero-rate >= intermittent_threshold → intermittent (Lane 3).
    5. Item in PERIODIC_PRODUCTS → periodic (Lane 2).
    6. Default → daily ML (Lane 1).

    Returns: 'daily' | 'periodic' | 'intermittent' | 'dormant'
    """
    if item_name in PRODUCT_LANES:
        return PRODUCT_LANES[item_name]

    if stats['n_days'] == 0:
        return 'dormant'

    if stats['zero_rate'] >= dormant_threshold:
        return 'dormant'

    if stats['zero_rate'] >= intermittent_threshold:
        return 'intermittent'

    if item_name in PERIODIC_PRODUCTS:
        return 'periodic'

    return 'daily'


# ── Lane 4: Dormant ──────────────────────────────────────────────────

def _build_dormant_forecast(store_id, item_id, plan_date, stats, window_days):
    """
    Lane 4 — Dormant: near-zero sustained demand; default to zero.
    Still assesses on-hand and propagates missing-snapshot warnings.
    """
    if stats['n_days'] > 0:
        explanations = [
            f"Dormant: {stats['n_order_days']}/{stats['n_days']} order-days "
            f"in {window_days}-day window (zero rate {stats['zero_rate']:.0%})"
        ]
    else:
        explanations = ['Dormant: no demand history in lookback window']

    warnings = ['dormant_product', 'sparse_usage_history', 'low_confidence']

    on_hand, on_hand_date, confidence = _assess_on_hand(
        store_id, item_id, plan_date, 'low', explanations, warnings,
        avg_daily_usage=Decimal('0'),
    )

    return {
        'avg_daily_usage': Decimal('0'),
        'confidence': confidence,
        'window_days': window_days,
        'data_points': stats['n_days'],
        'data_coverage': _compute_coverage(stats['n_days'], window_days),
        'data_source': 'actual_orders' if stats['n_order_days'] > 0 else 'none',
        'on_hand': on_hand,
        'on_hand_date': on_hand_date,
        'explanations': explanations,
        'warnings': warnings,
        'forecast_method': 'dormant_v1',
        'forecast_lane': 'dormant',
    }


# ── Lane 3: Intermittent ─────────────────────────────────────────────

def _build_intermittent_forecast(store_id, item_id, plan_date, stats, window_days):
    """
    Lane 3 — Intermittent: bursty, low-frequency demand.

    Expected daily demand = P(order today) × E[qty | order occurs].
    This avoids over-forecasting by not treating zero-order days as signal
    that demand is 0; instead it asks: when we do order, how much?
    """
    explanations = []
    warnings = ['intermittent_demand']

    n_days = stats['n_days']
    n_order_days = stats['n_order_days']
    avg_nonzero = stats['avg_nonzero']

    if n_order_days == 0:
        expected_daily = Decimal('0')
        confidence = 'low'
        warnings += ['sparse_usage_history', 'low_confidence']
        explanations.append('Intermittent: no orders in lookback window')
    else:
        order_freq = n_order_days / n_days
        expected_daily = Decimal(str(round(order_freq * avg_nonzero, 4)))
        explanations.append(
            f"Intermittent: {n_order_days} orders in {n_days} days "
            f"(freq {order_freq:.0%}, avg {avg_nonzero:.1f} when ordered "
            f"→ {float(expected_daily):.2f}/day expected)"
        )
        confidence = 'medium' if n_order_days >= 3 else 'low'
        if confidence == 'low':
            warnings += ['sparse_usage_history', 'low_confidence']

    on_hand, on_hand_date, confidence = _assess_on_hand(
        store_id, item_id, plan_date, confidence, explanations, warnings,
        avg_daily_usage=expected_daily,
    )

    return {
        'avg_daily_usage': expected_daily,
        'confidence': confidence,
        'window_days': window_days,
        'data_points': n_order_days,
        'data_coverage': _compute_coverage(n_days, window_days),
        'data_source': 'actual_orders' if n_order_days > 0 else 'none',
        'on_hand': on_hand,
        'on_hand_date': on_hand_date,
        'explanations': explanations,
        'warnings': warnings,
        'forecast_method': 'intermittent_v1',
        'forecast_lane': 'intermittent',
    }


# ── Lane 2: Periodic ─────────────────────────────────────────────────

def _build_periodic_forecast(store_id, item_id, plan_date, stats,
                              window_days, delivery_window):
    """
    Lane 2 — Periodic: products ordered on a regular 2-3 day cadence.

    Rather than predicting a daily quantity (which looks noisy because
    orders cluster), this lane computes:

        avg_daily_usage = avg_order_size / avg_inter_order_interval

    The resulting rate is smooth and correct over the delivery cycle.
    Downstream replenishment logic (par level, safety stock) applies as normal.
    """
    explanations = []
    warnings = ['periodic_demand']

    n_days = stats['n_days']
    n_order_days = stats['n_order_days']
    avg_nonzero = stats['avg_nonzero']

    if n_order_days == 0:
        expected_daily = Decimal('0')
        confidence = 'low'
        warnings += ['sparse_usage_history', 'low_confidence']
        explanations.append('Periodic: no orders in lookback window')
    else:
        avg_interval = n_days / n_order_days  # observed mean days between orders
        # Use the observed interval, but floor it at delivery_window to prevent
        # over-smoothing when the store orders more frequently than expected.
        effective_interval = max(avg_interval, float(delivery_window))
        expected_daily = Decimal(str(round(avg_nonzero / effective_interval, 4)))
        explanations.append(
            f"Periodic: {n_order_days} orders in {n_days} days "
            f"(avg interval {avg_interval:.1f}d, avg size {avg_nonzero:.1f} "
            f"→ {float(expected_daily):.2f}/day over {effective_interval:.1f}d window)"
        )
        confidence = 'medium' if n_order_days >= 4 else 'low'
        if confidence == 'low':
            warnings += ['sparse_usage_history', 'low_confidence']

    on_hand, on_hand_date, confidence = _assess_on_hand(
        store_id, item_id, plan_date, confidence, explanations, warnings,
        avg_daily_usage=expected_daily,
    )

    return {
        'avg_daily_usage': expected_daily,
        'confidence': confidence,
        'window_days': window_days,
        'data_points': n_order_days,
        'data_coverage': _compute_coverage(n_days, window_days),
        'data_source': 'actual_orders' if n_order_days > 0 else 'none',
        'on_hand': on_hand,
        'on_hand_date': on_hand_date,
        'explanations': explanations,
        'warnings': warnings,
        'forecast_method': 'periodic_v1',
        'forecast_lane': 'periodic',
    }


# ── Public dispatch ──────────────────────────────────────────────────

def build_forecast(store_id, item_id, plan_date):
    """
    Build a demand forecast for one store-item pair.

    Routes through a 4-lane system based on demand characteristics and
    explicit product overrides, then dispatches to the appropriate builder.

    Lane 1 — daily:       stable daily-use items; weighted or simple average.
    Lane 2 — periodic:    items ordered on a ~2-3 day cadence (cups, lids, sleeves).
    Lane 3 — intermittent: lumpy/bursty items; P(order) × E[qty|order].
    Lane 4 — dormant:     near-zero sustained demand; defaults to zero.

    Returns a dict with:
        avg_daily_usage:  Decimal — forecasted daily demand
        confidence:       str — 'high', 'medium', or 'low'
        window_days:      int — lookback window used
        data_points:      int — data points in the chosen window
        data_coverage:    float — fraction of window days with data (0.0-1.0)
        data_source:      str — 'actual_orders', 'daily_usage', or 'none'
        on_hand:          Decimal | None — latest on-hand quantity
        on_hand_date:     date | None — date of latest snapshot
        explanations:     list[str] — human-readable explanation steps
        warnings:         list[str] — warning flags
        forecast_method:  str — versioned method name
        forecast_lane:    str — routing lane ('daily'|'periodic'|'intermittent'|'dormant')
    """
    # ── Config ───────────────────────────────────────────────
    forecast_method = current_app.config.get('FORECAST_METHOD', 'historical_simple_v1')
    window_short = current_app.config.get('DEFAULT_USAGE_WINDOW_SHORT', 7)
    window_long = current_app.config.get('DEFAULT_USAGE_WINDOW_LONG', 14)
    min_data_points = current_app.config.get('MIN_DATA_POINTS_HIGH_CONFIDENCE', 5)
    routing_window = current_app.config.get('LANE_ROUTING_WINDOW', 28)
    dormant_threshold = current_app.config.get('LANE_DORMANT_ZERO_RATE', 0.95)
    intermittent_threshold = current_app.config.get('LANE_INTERMITTENT_ZERO_RATE', 0.65)
    delivery_window = current_app.config.get('LANE_PERIODIC_DELIVERY_WINDOW', 3)

    # Per-setting override for usage window (daily lane only)
    setting = StoreItemSetting.query.filter_by(
        store_id=store_id, item_id=item_id, active=True,
    ).first()
    if setting and setting.usage_window_days:
        window_short = setting.usage_window_days
        window_long = max(window_short * 2, window_long)

    # ── Route ────────────────────────────────────────────────
    item = db.session.get(InventoryItem, item_id)
    item_name = item.item_name if item else ''

    stats = _get_demand_stats(store_id, item_id, plan_date, routing_window)
    lane = _classify_lane(item_name, stats, dormant_threshold, intermittent_threshold)

    # ── Dispatch ─────────────────────────────────────────────
    if lane == 'dormant':
        return _build_dormant_forecast(store_id, item_id, plan_date, stats, routing_window)

    if lane == 'intermittent':
        return _build_intermittent_forecast(store_id, item_id, plan_date, stats, routing_window)

    if lane == 'periodic':
        return _build_periodic_forecast(
            store_id, item_id, plan_date, stats, routing_window, delivery_window)

    # Lane 1 — Daily ML
    if forecast_method == 'historical_weighted_v1':
        decay_factor = current_app.config.get('WEIGHTED_DECAY_FACTOR', 0.9)
        dow_multiplier = current_app.config.get('WEIGHTED_DOW_MULTIPLIER', 0.0)
        result = _build_weighted_forecast(
            store_id, item_id, plan_date,
            window_short, window_long, min_data_points,
            decay_factor, dow_multiplier,
        )
    else:
        result = _build_simple_forecast(
            store_id, item_id, plan_date,
            window_short, window_long, min_data_points,
        )
    result['forecast_lane'] = 'daily'
    return result
