"""
Plan generation service.

Orchestrates the creation of a replenishment plan for a given date.
"""
from datetime import datetime, timezone

from warehouse_app.extensions import db
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.store_item_setting import StoreItemSetting
from warehouse_app.models.replenishment_plan import ReplenishmentPlan
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine
from warehouse_app.services.recommendation import calculate_recommendation


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
        # Delete existing draft lines and plan
        ReplenishmentPlanLine.query.filter_by(plan_id=existing.id).delete()
        db.session.delete(existing)
        db.session.flush()

    # Create new plan
    plan = ReplenishmentPlan(
        plan_date=plan_date,
        status='draft',
        generated_at=datetime.now(timezone.utc),
        generated_by_user_id=user_id,
    )
    db.session.add(plan)
    db.session.flush()

    # Get all active store-item settings
    active_settings = StoreItemSetting.query.filter_by(active=True).all()

    # Also track active stores and items for combinations without explicit settings
    active_stores = Store.query.filter_by(active=True).all()
    active_items = InventoryItem.query.filter_by(active=True).all()

    # Build set of (store_id, item_id) with settings
    settings_pairs = {(s.store_id, s.item_id) for s in active_settings}

    # Generate lines only for store-item pairs that have settings
    lines = []
    stats = {
        'total_lines': 0,
        'low_confidence': 0,
        'warnings': 0,
        'stores': set(),
    }

    for store_id, item_id in settings_pairs:
        rec = calculate_recommendation(store_id, item_id, plan_date)

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
        )
        lines.append(line)

        stats['total_lines'] += 1
        stats['stores'].add(store_id)
        if rec['confidence_level'] == 'low':
            stats['low_confidence'] += 1
        if rec['warning_flags']:
            stats['warnings'] += 1

    db.session.add_all(lines)
    db.session.commit()

    return {
        'plan': plan,
        'total_lines': stats['total_lines'],
        'total_stores': len(stats['stores']),
        'low_confidence': stats['low_confidence'],
        'warnings': stats['warnings'],
    }
