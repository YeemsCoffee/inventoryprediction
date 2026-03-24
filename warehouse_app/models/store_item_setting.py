from datetime import datetime, timezone

from warehouse_app.extensions import db


class StoreItemSetting(db.Model):
    __tablename__ = 'store_item_settings'

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False, index=True)
    par_level = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    safety_stock = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    reorder_threshold = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    min_send_quantity = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    rounding_rule = db.Column(
        db.String(30),
        nullable=False,
        default='none',
    )
    usage_window_days = db.Column(db.Integer, nullable=True)  # override app default per store-item
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint('store_id', 'item_id', name='uq_store_item_settings_store_item'),
        db.CheckConstraint('par_level >= 0', name='ck_store_item_settings_par_level'),
        db.CheckConstraint('safety_stock >= 0', name='ck_store_item_settings_safety_stock'),
        db.CheckConstraint('reorder_threshold >= 0', name='ck_store_item_settings_reorder_threshold'),
        db.CheckConstraint('min_send_quantity >= 0', name='ck_store_item_settings_min_send_quantity'),
        db.CheckConstraint(
            "rounding_rule IN ('none', 'round_up_integer', 'round_up_case_pack')",
            name='ck_store_item_settings_rounding_rule',
        ),
    )

    # Relationships
    store = db.relationship('Store', back_populates='store_item_settings')
    item = db.relationship('InventoryItem', back_populates='store_item_settings')

    def __repr__(self):
        return f'<StoreItemSetting store={self.store_id} item={self.item_id}>'
