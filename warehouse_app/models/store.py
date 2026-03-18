from datetime import datetime, timezone

from warehouse_app.extensions import db


class Store(db.Model):
    __tablename__ = 'stores'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    store_item_settings = db.relationship('StoreItemSetting', back_populates='store', lazy='dynamic')
    daily_usages = db.relationship('DailyUsage', back_populates='store', lazy='dynamic')
    inventory_snapshots = db.relationship('InventorySnapshot', back_populates='store', lazy='dynamic')
    replenishment_plan_lines = db.relationship('ReplenishmentPlanLine', back_populates='store', lazy='dynamic')

    def __repr__(self):
        return f'<Store {self.code}>'
