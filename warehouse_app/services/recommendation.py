"""
Recommendation engine for warehouse replenishment.

Rules-based, transparent logic. No ML.
Forecasts for the next day only (daily delivery cadence).
"""
import math
from datetime import timedelta
from decimal import Decimal, ROUND_CEILING

from flask import current_app
from sqlalchemy import func

from warehouse_app.extensions import db
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot
from warehouse_app.models.store_item_setting import StoreItemSetting
from warehouse_app.models.inventory_item import InventoryItem


def _to_decimal(val):
    """Safely convert to Decimal."""
    if val is None:
        return Decimal('0')
    return Decimal(str(val))


def get_average_usage(store_id, item_id, plan_date, days):
    """Return average daily usage over the given window ending the day before plan_date."""
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
    """Return the latest inventory snapshot quantity on or before plan_date."""
    snapshot = InventorySnapshot.query.filter(
        InventorySnapshot.store_id == store_id,
        InventorySnapshot.item_id == item_id,
        InventorySnapshot.snapshot_date <= plan_date,
    ).order_by(InventorySnapshot.snapshot_date.desc()).first()

    if snapshot is None:
        return None, None
    return _to_decimal(snapshot.quantity_on_hand), snapshot.snapshot_date


def apply_rounding(quantity, rounding_rule, case_pack_quantity):
    """Apply rounding rule to a quantity. Returns Decimal."""
    if quantity <= 0:
        return Decimal('0')

    if rounding_rule == 'round_up_integer':
        return quantity.to_integral_value(rounding=ROUND_CEILING)

    if rounding_rule == 'round_up_case_pack':
        cpq = Decimal(str(case_pack_quantity))
        if cpq <= 0:
            cpq = Decimal('1')
        return (quantity / cpq).to_integral_value(rounding=ROUND_CEILING) * cpq

    # 'none' — return as-is
    return quantity


def calculate_recommendation(store_id, item_id, plan_date):
    """
    Calculate the replenishment recommendation for one store-item pair.

    Returns a dict with:
        recommended_quantity, confidence_level, explanation_text, warning_flags,
        forecast_avg_daily_usage, forecast_on_hand, forecast_target, forecast_window_days
    """
    # Read config values
    window_short = current_app.config.get('DEFAULT_USAGE_WINDOW_SHORT', 7)
    window_long = current_app.config.get('DEFAULT_USAGE_WINDOW_LONG', 14)
    min_data_points = current_app.config.get('MIN_DATA_POINTS_HIGH_CONFIDENCE', 5)

    setting = StoreItemSetting.query.filter_by(
        store_id=store_id, item_id=item_id, active=True,
    ).first()

    item = db.session.get(InventoryItem, item_id)

    # Defaults if no setting exists
    par_level = _to_decimal(setting.par_level) if setting else Decimal('0')
    safety_stock = _to_decimal(setting.safety_stock) if setting else Decimal('0')
    min_send = _to_decimal(setting.min_send_quantity) if setting else Decimal('0')
    rounding_rule = setting.rounding_rule if setting else 'none'
    case_pack_qty = item.case_pack_quantity if item else 1

    # Per-setting override for usage window
    effective_window_short = setting.usage_window_days if (setting and setting.usage_window_days) else window_short
    effective_window_long = max(effective_window_short * 2, window_long)

    explanations = []
    warnings = []
    confidence = 'high'

    # ── Step 1: Get usage forecast ──────────────────────────
    avg_short, count_short = get_average_usage(store_id, item_id, plan_date, effective_window_short)
    avg_long, count_long = get_average_usage(store_id, item_id, plan_date, effective_window_long)

    forecast_window_used = effective_window_short

    if count_short >= min_data_points:
        forecast_daily = avg_short
        explanations.append(f'Based on {effective_window_short}-day average usage')
        confidence = 'high'
    elif count_long >= min_data_points:
        forecast_daily = avg_long
        forecast_window_used = effective_window_long
        explanations.append(f'Based on {effective_window_long}-day average usage (insufficient {effective_window_short}-day data)')
        confidence = 'medium'
    elif count_short > 0 or count_long > 0:
        # Use whatever we have
        forecast_daily = avg_long if count_long > count_short else avg_short
        forecast_window_used = effective_window_long if count_long > count_short else effective_window_short
        explanations.append('Limited usage history available')
        confidence = 'low'
        warnings.append('sparse_usage_history')
    else:
        # No usage data at all — fall back to par level
        forecast_daily = par_level
        forecast_window_used = 0
        explanations.append('No usage history — using par level as fallback')
        confidence = 'low'
        warnings.append('sparse_usage_history')

    if confidence == 'low':
        warnings.append('low_confidence')

    # ── Step 2: Get current on-hand ─────────────────────────
    on_hand, snapshot_date = get_latest_on_hand(store_id, item_id, plan_date)

    if on_hand is None:
        on_hand = Decimal('0')
        warnings.append('missing_snapshot')
        explanations.append('No inventory snapshot found — assuming 0 on hand')
        if confidence == 'high':
            confidence = 'medium'
    else:
        explanations.append(f'On-hand: {on_hand} (as of {snapshot_date})')

    # ── Step 3: Calculate target ────────────────────────────
    target = max(par_level, forecast_daily + safety_stock)

    # ── Step 4: Calculate needed quantity ────────────────────
    needed = target - on_hand
    if needed < 0:
        needed = Decimal('0')

    # ── Step 5: Apply min send quantity ─────────────────────
    if needed > 0 and needed < min_send:
        needed = min_send
        explanations.append(f'Raised to minimum send quantity ({min_send})')

    # ── Step 6: Apply rounding ──────────────────────────────
    pre_round = needed
    needed = apply_rounding(needed, rounding_rule, case_pack_qty)
    if needed != pre_round and needed > 0:
        if rounding_rule == 'round_up_case_pack':
            explanations.append(f'Rounded up to case pack of {case_pack_qty}')
        elif rounding_rule == 'round_up_integer':
            explanations.append('Rounded up to whole unit')

    # ── Step 7: Flag unusual recommendations ────────────────
    if needed > par_level * 2 and par_level > 0:
        warnings.append('unusual_recommendation')

    return {
        'recommended_quantity': needed,
        'confidence_level': confidence,
        'explanation_text': '. '.join(explanations) + '.',
        'warning_flags': warnings,
        # Forecast metadata for audit trail / transparency
        'forecast_avg_daily_usage': forecast_daily,
        'forecast_on_hand': on_hand,
        'forecast_target': target,
        'forecast_window_days': forecast_window_used,
    }
