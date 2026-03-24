from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from warehouse_app.blueprints.admin import admin_bp
from warehouse_app.auth_helpers import admin_required
from warehouse_app.extensions import db
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.store_item_setting import StoreItemSetting


# ── Stores ──────────────────────────────────────────────────

@admin_bp.route('/stores')
@login_required
@admin_required
def stores():
    all_stores = Store.query.order_by(Store.name).all()
    return render_template('admin/stores.html', stores=all_stores)


@admin_bp.route('/stores/new', methods=['GET', 'POST'])
@login_required
@admin_required
def store_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        active = request.form.get('active') == 'on'

        if not name or not code:
            flash('Name and code are required.', 'danger')
            return render_template('admin/store_form.html', store=None)

        if len(name) > 200 or len(code) > 50:
            flash('Name must be 200 characters or fewer, code 50 or fewer.', 'danger')
            return render_template('admin/store_form.html', store=None)

        if Store.query.filter_by(code=code).first():
            flash(f'Store code "{code}" already exists.', 'danger')
            return render_template('admin/store_form.html', store=None)

        address = request.form.get('address', '').strip() or None
        delivery_schedule = request.form.get('delivery_schedule', '').strip() or None

        store = Store(name=name, code=code, address=address,
                      delivery_schedule=delivery_schedule, active=active)
        db.session.add(store)
        db.session.commit()
        flash(f'Store "{name}" created.', 'success')
        return redirect(url_for('admin.stores'))

    return render_template('admin/store_form.html', store=None)


@admin_bp.route('/stores/<int:store_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def store_edit(store_id):
    store = Store.query.get_or_404(store_id)

    if request.method == 'POST':
        store.name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        store.active = request.form.get('active') == 'on'

        if not store.name or not code:
            flash('Name and code are required.', 'danger')
            return render_template('admin/store_form.html', store=store)

        existing = Store.query.filter_by(code=code).first()
        if existing and existing.id != store.id:
            flash(f'Store code "{code}" already exists.', 'danger')
            return render_template('admin/store_form.html', store=store)

        store.code = code
        store.address = request.form.get('address', '').strip() or None
        store.delivery_schedule = request.form.get('delivery_schedule', '').strip() or None
        db.session.commit()
        flash(f'Store "{store.name}" updated.', 'success')
        return redirect(url_for('admin.stores'))

    return render_template('admin/store_form.html', store=store)


# ── Inventory Items ─────────────────────────────────────────

@admin_bp.route('/items')
@login_required
@admin_required
def items():
    all_items = InventoryItem.query.order_by(InventoryItem.category, InventoryItem.item_name).all()
    return render_template('admin/items.html', items=all_items)


@admin_bp.route('/items/new', methods=['GET', 'POST'])
@login_required
@admin_required
def item_new():
    if request.method == 'POST':
        return _save_item(None)
    return render_template('admin/item_form.html', item=None)


@admin_bp.route('/items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def item_edit(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    if request.method == 'POST':
        return _save_item(item)
    return render_template('admin/item_form.html', item=item)


def _save_item(item):
    name = request.form.get('item_name', '').strip()
    sku = request.form.get('sku', '').strip().upper()
    category = request.form.get('category', '').strip()
    uom = request.form.get('unit_of_measure', '').strip()
    cpq = request.form.get('case_pack_quantity', '1').strip()
    active = request.form.get('active') == 'on'

    if not name or not sku:
        flash('Item name and SKU are required.', 'danger')
        return render_template('admin/item_form.html', item=item)

    if len(name) > 200 or len(sku) > 50:
        flash('Item name must be 200 characters or fewer, SKU 50 or fewer.', 'danger')
        return render_template('admin/item_form.html', item=item)

    try:
        cpq = int(cpq)
        if cpq < 1:
            raise ValueError
    except ValueError:
        flash('Case pack quantity must be a positive integer.', 'danger')
        return render_template('admin/item_form.html', item=item)

    existing = InventoryItem.query.filter_by(sku=sku).first()
    if existing and (item is None or existing.id != item.id):
        flash(f'SKU "{sku}" already exists.', 'danger')
        return render_template('admin/item_form.html', item=item)

    if item is None:
        item = InventoryItem()
        db.session.add(item)

    description = request.form.get('description', '').strip() or None
    storage_type = request.form.get('storage_type', '').strip() or None

    item.item_name = name
    item.sku = sku
    item.category = category
    item.description = description
    item.unit_of_measure = uom
    item.case_pack_quantity = cpq
    item.storage_type = storage_type
    item.active = active

    db.session.commit()
    flash(f'Item "{name}" saved.', 'success')
    return redirect(url_for('admin.items'))


# ── Store Item Settings ─────────────────────────────────────

@admin_bp.route('/store-item-settings')
@login_required
@admin_required
def store_item_settings():
    store_id = request.args.get('store_id', type=int)
    query = StoreItemSetting.query

    if store_id:
        query = query.filter_by(store_id=store_id)

    settings = query.order_by(StoreItemSetting.store_id, StoreItemSetting.item_id).all()
    all_stores = Store.query.order_by(Store.name).all()
    return render_template('admin/store_item_settings.html',
                           settings=settings, stores=all_stores,
                           selected_store_id=store_id)


@admin_bp.route('/store-item-settings/new', methods=['GET', 'POST'])
@login_required
@admin_required
def setting_new():
    if request.method == 'POST':
        return _save_setting(None)
    stores = Store.query.filter_by(active=True).order_by(Store.name).all()
    items = InventoryItem.query.filter_by(active=True).order_by(InventoryItem.item_name).all()
    return render_template('admin/store_item_setting_form.html',
                           setting=None, stores=stores, items=items)


@admin_bp.route('/store-item-settings/<int:setting_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def setting_edit(setting_id):
    setting = StoreItemSetting.query.get_or_404(setting_id)
    if request.method == 'POST':
        return _save_setting(setting)
    stores = Store.query.filter_by(active=True).order_by(Store.name).all()
    items = InventoryItem.query.filter_by(active=True).order_by(InventoryItem.item_name).all()
    # Ensure the setting's current item/store appear even if inactive
    if setting.item and setting.item not in items:
        items.append(setting.item)
    if setting.store and setting.store not in stores:
        stores.append(setting.store)
    return render_template('admin/store_item_setting_form.html',
                           setting=setting, stores=stores, items=items)


def _save_setting(setting):
    store_id = request.form.get('store_id', type=int)
    item_id = request.form.get('item_id', type=int)

    try:
        par_level = float(request.form.get('par_level', 0))
        safety_stock = float(request.form.get('safety_stock', 0))
        reorder_threshold = float(request.form.get('reorder_threshold', 0))
        min_send_quantity = float(request.form.get('min_send_quantity', 0))
    except (ValueError, TypeError):
        flash('Numeric fields must be valid numbers.', 'danger')
        return redirect(request.url)

    if any(v < 0 for v in [par_level, safety_stock, reorder_threshold, min_send_quantity]):
        flash('Numeric fields must be non-negative.', 'danger')
        return redirect(request.url)

    rounding_rule = request.form.get('rounding_rule', 'none')
    active = request.form.get('active') == 'on'

    if not store_id or not item_id:
        flash('Store and item are required.', 'danger')
        return redirect(request.url)

    if rounding_rule not in ('none', 'round_up_integer', 'round_up_case_pack'):
        flash('Invalid rounding rule.', 'danger')
        return redirect(request.url)

    # Parse usage_window_days (optional override) — validate before creating object
    usage_window_str = request.form.get('usage_window_days', '').strip()
    usage_window_days = None
    if usage_window_str:
        try:
            usage_window_days = int(usage_window_str)
            if usage_window_days < 1 or usage_window_days > 90:
                flash('Usage window must be between 1 and 90 days.', 'danger')
                return redirect(request.url)
        except ValueError:
            flash('Usage window must be a whole number.', 'danger')
            return redirect(request.url)

    # Check uniqueness
    existing = StoreItemSetting.query.filter_by(store_id=store_id, item_id=item_id).first()
    if existing and (setting is None or existing.id != setting.id):
        flash('A setting already exists for this store-item pair.', 'danger')
        return redirect(request.url)

    if setting is None:
        setting = StoreItemSetting()
        db.session.add(setting)

    setting.store_id = store_id
    setting.item_id = item_id
    setting.par_level = par_level
    setting.safety_stock = safety_stock
    setting.reorder_threshold = reorder_threshold
    setting.min_send_quantity = min_send_quantity
    setting.rounding_rule = rounding_rule
    setting.usage_window_days = usage_window_days
    setting.active = active

    db.session.commit()
    flash('Store item setting saved.', 'success')
    return redirect(url_for('admin.store_item_settings'))
