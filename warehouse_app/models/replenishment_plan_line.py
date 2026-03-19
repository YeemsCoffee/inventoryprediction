from datetime import datetime, timezone

from warehouse_app.extensions import db


class ReplenishmentPlanLine(db.Model):
    __tablename__ = 'replenishment_plan_lines'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('replenishment_plans.id'), nullable=False, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False, index=True)
    recommended_quantity = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    actual_quantity = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default='pending',
    )
    confidence_level = db.Column(
        db.String(10),
        nullable=False,
        default='high',
    )
    explanation_text = db.Column(db.Text, nullable=True)
    warning_flags = db.Column(db.JSON, nullable=False, default=list)
    picker_note = db.Column(db.Text, nullable=True)
    last_status_change_at = db.Column(db.DateTime, nullable=True)

    # ── Forecast metadata (captures inputs used for recommendation) ───
    forecast_method = db.Column(db.String(30), nullable=True, default='simple_average')
    forecast_avg_daily_usage = db.Column(db.Numeric(10, 4), nullable=True)
    forecast_on_hand = db.Column(db.Numeric(10, 2), nullable=True)
    forecast_target = db.Column(db.Numeric(10, 2), nullable=True)
    forecast_window_days = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint('plan_id', 'store_id', 'item_id', name='uq_plan_line_plan_store_item'),
        db.Index('ix_plan_lines_plan_status', 'plan_id', 'status'),
        db.CheckConstraint('recommended_quantity >= 0', name='ck_plan_line_recommended_qty'),
        db.CheckConstraint(
            "status IN ('pending', 'picked', 'loaded', 'delivered', 'shorted')",
            name='ck_plan_line_status',
        ),
        db.CheckConstraint(
            "confidence_level IN ('high', 'medium', 'low')",
            name='ck_plan_line_confidence',
        ),
    )

    # Relationships
    plan = db.relationship('ReplenishmentPlan', back_populates='lines')
    store = db.relationship('Store', back_populates='replenishment_plan_lines')
    item = db.relationship('InventoryItem', back_populates='replenishment_plan_lines')

    def __repr__(self):
        return f'<PlanLine plan={self.plan_id} store={self.store_id} item={self.item_id} status={self.status}>'
