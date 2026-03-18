"""
Plan generation service.

Orchestrates the creation of a replenishment plan for a given date.
"""
from datetime import datetime, timezone

from flask import current_app

from warehouse_app.extensions import db
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.store_item_setting import StoreItemSetting
from warehouse_app.models.replenishment_plan import ReplenishmentPlan
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine
from warehouse_app.services.replenishment import calculate_recommendation
from warehouse_app.services.audit import log_action


def generate_plan(plan_date, user_id, regenerate=False):
    """
    Generate a replenishment plan for the given date.

    Args:
        plan_date: date object for the delivery date
        user_id: ID of the user generating the plan
        regenerate: if True, delete existing draft plan and regenerate

    Returns:
        dict with plan object and summary stats

    Raises:
        ValueError if a non-draft plan already exists for that date
    """
    existing = ReplenishmentPlan.query.filter_by(plan_date=plan_date).first()

    if existing:
        if not regenerate:
            raise ValueError(
                f'A plan already exists for {plan_date} (status: {existing.status}). '
                'Check "Regenerate" to replace a draft plan.'
            )
        if existing.status != 'draft':
            raise ValueError(
                f'Cannot regenerate a plan with status "{existing.status}". '
                'Only draft plans can be regenerated.'
            )
        # Log the regeneration before deleting
        log_action('plan', existing.id, 'regenerate',
                   old_value=f'plan_date={plan_date}, lines={existing.lines.count()}')
        # Delete existing draft lines and plan
        ReplenishmentPlanLine.query.filter_by(plan_id=existing.id).delete()
        db.session.delete(existing)
        db.session.flush()

    # Verify there are active settings to generate from
    active_settings = StoreItemSetting.query.filter_by(active=True).all()
    if not active_settings:
        raise ValueError(
            'No active store-item settings found. '
            'Create settings in Admin > Store Item Settings before generating a plan.'
        )

    # Create new plan
    plan = ReplenishmentPlan(
        plan_date=plan_date,
        status='draft',
        generated_at=datetime.now(timezone.utc),
        generated_by_user_id=user_id,
    )
    db.session.add(plan)
    db.session.flush()

    # Build set of (store_id, item_id) with settings
    settings_pairs = {(s.store_id, s.item_id) for s in active_settings}

    # Generate lines only for store-item pairs that have settings
    lines = []
    stats = {
        'total_lines': 0,
        'low_confidence': 0,
        'warnings': 0,
        'stores': set(),
        'zero_qty_skipped': 0,
    }

    for store_id, item_id in settings_pairs:
        rec = calculate_recommendation(store_id, item_id, plan_date)

        # Skip lines with zero recommended quantity to keep plans clean
        if rec['recommended_quantity'] <= 0:
            stats['zero_qty_skipped'] += 1
            continue

        line = ReplenishmentPlanLine(
            plan_id=plan.id,
            store_id=store_id,
            item_id=item_id,
            recommended_quantity=rec['recommended_quantity'],
            actual_quantity=None,
            status='pending',
            confidence_level=rec['confidence_level'],
            explanation_text=rec['explanation_text'],
            warning_flags=rec['warning_flags'],
            # Forecast metadata
            forecast_avg_daily_usage=rec['forecast_avg_daily_usage'],
            forecast_on_hand=rec['forecast_on_hand'],
            forecast_target=rec['forecast_target'],
            forecast_window_days=rec['forecast_window_days'],
        )
        lines.append(line)

        stats['total_lines'] += 1
        stats['stores'].add(store_id)
        if rec['confidence_level'] == 'low':
            stats['low_confidence'] += 1
        if rec['warning_flags']:
            stats['warnings'] += 1

    db.session.add_all(lines)

    log_action('plan', plan.id, 'generate',
               new_value=f'plan_date={plan_date}, lines={stats["total_lines"]}, '
                         f'stores={len(stats["stores"])}, '
                         f'low_confidence={stats["low_confidence"]}, '
                         f'warnings={stats["warnings"]}')

    db.session.commit()

    return {
        'plan': plan,
        'total_lines': stats['total_lines'],
        'total_stores': len(stats['stores']),
        'low_confidence': stats['low_confidence'],
        'warnings': stats['warnings'],
        'zero_qty_skipped': stats['zero_qty_skipped'],
    }
