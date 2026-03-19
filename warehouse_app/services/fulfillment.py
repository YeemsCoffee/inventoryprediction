"""
Fulfillment service — handles status updates on plan lines.
"""
from datetime import datetime, timezone

from warehouse_app.extensions import db
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine
from warehouse_app.services.audit import log_action

VALID_STATUSES = ('pending', 'picked', 'loaded', 'delivered', 'shorted')


def update_line_status(line_id, new_status=None, actual_quantity=None, picker_note=None):
    """
    Update status and/or actual_quantity / picker_note on a plan line.

    Returns the updated line or raises ValueError.
    """
    line = db.session.get(ReplenishmentPlanLine, line_id)
    if line is None:
        raise ValueError(f'Plan line {line_id} not found')

    changes = []

    if new_status is not None:
        if new_status not in VALID_STATUSES:
            raise ValueError(f'Invalid status: {new_status}')
        old_status = line.status
        line.status = new_status
        line.last_status_change_at = datetime.now(timezone.utc)
        changes.append(f'status: {old_status} -> {new_status}')

    if actual_quantity is not None:
        old_qty = float(line.actual_quantity) if line.actual_quantity is not None else None
        line.actual_quantity = actual_quantity
        changes.append(f'actual_qty: {old_qty} -> {actual_quantity}')

    if picker_note is not None:
        line.picker_note = str(picker_note)[:500]
        changes.append(f'note updated')

    if changes:
        log_action('plan_line', line.id, 'update', new_value='; '.join(changes))

    db.session.commit()
    return line


def bulk_update_status(line_ids, new_status):
    """Update status for multiple lines at once."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f'Invalid status: {new_status}')

    now = datetime.now(timezone.utc)
    count = ReplenishmentPlanLine.query.filter(
        ReplenishmentPlanLine.id.in_(line_ids)
    ).update({
        ReplenishmentPlanLine.status: new_status,
        ReplenishmentPlanLine.last_status_change_at: now,
    }, synchronize_session='fetch')

    for line_id in line_ids:
        log_action('plan_line', line_id, 'bulk_update', new_value=f'status -> {new_status}')

    db.session.commit()
    return count
