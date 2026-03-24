"""
Lightweight audit logging helper.
"""
from flask_login import current_user

from warehouse_app.extensions import db
from warehouse_app.models.audit_log import AuditLog


def log_action(entity_type, entity_id, action, old_value=None, new_value=None):
    """Write an audit log entry."""
    user_id = current_user.id if current_user and current_user.is_authenticated else None
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        changed_by_user_id=user_id,
    )
    db.session.add(entry)
    # Don't commit here — caller controls the transaction
