from datetime import datetime, timezone

from warehouse_app.extensions import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(100), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(50), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    changed_by_user_id = db.Column(db.Integer, nullable=True)
    changed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<AuditLog {self.entity_type}#{self.entity_id} {self.action}>'
