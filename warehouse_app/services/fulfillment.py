"""
Fulfillment service — handles status updates on plan lines.
"""
from datetime import datetime, timezone

from warehouse_app.extensions import db
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine

VALID_STATUSES = ('pending', 'picked', 'loaded', 'delivered', 'shorted')


def update_line_status(line_id, new_status, actual_quantity=None, picker_note=None):
    """
    Update status and optionally actual_quantity / picker_note on a plan line.

    Returns the updated line or raises ValueError.
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(f'Invalid status: {new_status}')

    line = ReplenishmentPlanLine.query.get(line_id)
    if line is None:
        raise ValueError(f'Plan line {line_id} not found')

    line.status = new_status
    line.last_status_change_at = datetime.now(timezone.utc)

    if actual_quantity is not None:
        line.actual_quantity = actual_quantity

    if picker_note is not None:
        line.picker_note = picker_note

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

    db.session.commit()
    return count
