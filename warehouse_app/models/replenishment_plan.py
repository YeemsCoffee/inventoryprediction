from datetime import datetime, timezone

from warehouse_app.extensions import db


class ReplenishmentPlan(db.Model):
    __tablename__ = 'replenishment_plans'

    id = db.Column(db.Integer, primary_key=True)
    plan_date = db.Column(db.Date, nullable=False, unique=True, index=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default='draft',
    )
    generated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    generated_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('draft', 'in_progress', 'completed')",
            name='ck_replenishment_plans_status',
        ),
    )

    # Relationships
    generated_by_user = db.relationship('User', back_populates='replenishment_plans')
    lines = db.relationship(
        'ReplenishmentPlanLine',
        back_populates='plan',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    @property
    def is_draft(self):
        return self.status == 'draft'

    def __repr__(self):
        return f'<ReplenishmentPlan date={self.plan_date} status={self.status}>'
