"""
Replenishment calculation service.

Consumes demand forecast output and applies business rules
(par levels, safety stock, min-send, rounding) to produce
a replenishment recommendation for one store-item pair.

Does NOT contain forecasting logic — that lives in forecasting.py.
Does NOT handle fulfillment/execution — that lives in fulfillment.py.
"""
from decimal import Decimal, ROUND_CEILING

from warehouse_app.extensions import db
from warehouse_app.models.store_item_setting import StoreItemSetting
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.services.forecasting import build_forecast


def _to_decimal(val):
    """Safely convert to Decimal."""
    if val is None:
        return Decimal('0')
    return Decimal(str(val))


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

    Delegates demand forecasting to forecasting.build_forecast(), then applies
    replenishment business rules (par level, safety stock, min-send, rounding).

    Returns a dict with:
        recommended_quantity: Decimal
        confidence_level: str
        explanation_text: str
        warning_flags: list[str]
        forecast_avg_daily_usage: Decimal
        forecast_on_hand: Decimal
        forecast_target: Decimal
        forecast_window_days: int
    """
    # ── Step 1: Get demand forecast ─────────────────────────
    forecast = build_forecast(store_id, item_id, plan_date)

    avg_daily_usage = forecast['avg_daily_usage']
    on_hand = forecast['on_hand'] if forecast['on_hand'] is not None else Decimal('0')
    confidence = forecast['confidence']
    explanations = list(forecast['explanations'])
    warnings = list(forecast['warnings'])

    # ── Step 2: Load replenishment settings ──────────────────
    setting = StoreItemSetting.query.filter_by(
        store_id=store_id, item_id=item_id, active=True,
    ).first()
    item = db.session.get(InventoryItem, item_id)

    par_level = _to_decimal(setting.par_level) if setting else Decimal('0')
    safety_stock = _to_decimal(setting.safety_stock) if setting else Decimal('0')
    min_send = _to_decimal(setting.min_send_quantity) if setting else Decimal('0')
    rounding_rule = setting.rounding_rule if setting else 'none'
    case_pack_qty = item.case_pack_quantity if item else 1

    # If no usage data and no snapshot, fall back to par level as demand estimate
    if avg_daily_usage == 0 and forecast['data_points'] == 0:
        avg_daily_usage = par_level
        explanations.append('Using par level as fallback demand estimate')

    # ── Step 3: Calculate target ────────────────────────────
    target = max(par_level, avg_daily_usage + safety_stock)

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
        'forecast_avg_daily_usage': avg_daily_usage,
        'forecast_on_hand': on_hand,
        'forecast_target': target,
        'forecast_window_days': forecast['window_days'],
    }
