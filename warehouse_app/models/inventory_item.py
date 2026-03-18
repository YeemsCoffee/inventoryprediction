from datetime import datetime, timezone

from warehouse_app.extensions import db


class InventoryItem(db.Model):
    __tablename__ = 'inventory_items'

    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(100), nullable=False, unique=True, index=True)
    category = db.Column(db.String(100), nullable=False, default='')
    description = db.Column(db.Text, nullable=True)
    unit_of_measure = db.Column(db.String(50), nullable=False, default='each')
    case_pack_quantity = db.Column(db.Integer, nullable=False, default=1)
    storage_type = db.Column(db.String(50), nullable=True)  # e.g. 'refrigerated', 'dry', 'frozen'
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.CheckConstraint('case_pack_quantity > 0', name='ck_inventory_items_case_pack_positive'),
    )

    # Relationships
    store_item_settings = db.relationship('StoreItemSetting', back_populates='item', lazy='dynamic')
    daily_usages = db.relationship('DailyUsage', back_populates='item', lazy='dynamic')
    inventory_snapshots = db.relationship('InventorySnapshot', back_populates='item', lazy='dynamic')
    replenishment_plan_lines = db.relationship('ReplenishmentPlanLine', back_populates='item', lazy='dynamic')

    def __repr__(self):
        return f'<InventoryItem {self.sku}>'
