from datetime import datetime, timezone

from warehouse_app.extensions import db


class ActualOrder(db.Model):
    __tablename__ = 'actual_orders'

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False, index=True)
    order_date = db.Column(db.Date, nullable=False, index=True)
    quantity_ordered = db.Column(db.Numeric(10, 2), nullable=False)
    source = db.Column(db.String(50), nullable=False, default='manual')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('store_id', 'item_id', 'order_date', name='uq_actual_order_store_item_date'),
        db.CheckConstraint('quantity_ordered >= 0', name='ck_actual_order_quantity_positive'),
    )

    # Relationships
    store = db.relationship('Store', back_populates='actual_orders')
    item = db.relationship('InventoryItem', back_populates='actual_orders')

    def __repr__(self):
        return f'<ActualOrder store={self.store_id} item={self.item_id} date={self.order_date}>'
