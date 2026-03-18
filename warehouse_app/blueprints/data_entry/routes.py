from datetime import datetime

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from warehouse_app.blueprints.data_entry import data_entry_bp
from warehouse_app.auth_helpers import admin_required
from warehouse_app.extensions import db
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot
from warehouse_app.services.csv_import import (
    import_daily_usage_csv,
    import_inventory_snapshot_csv,
)


# ── Daily Usage ─────────────────────────────────────────────

@data_entry_bp.route('/daily-usage', methods=['GET', 'POST'])
@login_required
@admin_required
def daily_usage():
    stores = Store.query.filter_by(active=True).order_by(Store.name).all()
    items = InventoryItem.query.filter_by(active=True).order_by(InventoryItem.item_name).all()

    if request.method == 'POST':
        store_id = request.form.get('store_id', type=int)
        item_id = request.form.get('item_id', type=int)
        date_str = request.form.get('usage_date', '').strip()
        qty_str = request.form.get('quantity_used', '').strip()
        notes = request.form.get('notes', '').strip() or None

        if not store_id or not item_id or not date_str or not qty_str:
            flash('All fields except notes are required.', 'danger')
            return render_template('data_entry/daily_usage.html', stores=stores, items=items)

        try:
            usage_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('data_entry/daily_usage.html', stores=stores, items=items)

        try:
            quantity = float(qty_str)
            if quantity < 0:
                raise ValueError
        except ValueError:
            flash('Quantity must be a non-negative number.', 'danger')
            return render_template('data_entry/daily_usage.html', stores=stores, items=items)

        existing = DailyUsage.query.filter_by(
            store_id=store_id, item_id=item_id, usage_date=usage_date,
        ).first()

        if existing:
            existing.quantity_used = quantity
            existing.source = 'manual'
            existing.notes = notes
        else:
            db.session.add(DailyUsage(
                store_id=store_id, item_id=item_id,
                usage_date=usage_date, quantity_used=quantity,
                source='manual', notes=notes,
            ))

        db.session.commit()
        flash('Daily usage saved.', 'success')
        return redirect(url_for('data_entry.daily_usage'))

    return render_template('data_entry/daily_usage.html', stores=stores, items=items)


@data_entry_bp.route('/daily-usage/import', methods=['POST'])
@login_required
@admin_required
def daily_usage_import():
    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a .csv file.', 'danger')
        return redirect(url_for('data_entry.daily_usage'))

    content = file.read().decode('utf-8-sig')
    result = import_daily_usage_csv(content)

    flash(f'Import complete: {result["imported"]} imported, {result["skipped"]} skipped.', 'success')
    if result['errors']:
        for err in result['errors'][:10]:
            flash(err, 'warning')
        if len(result['errors']) > 10:
            flash(f'...and {len(result["errors"]) - 10} more errors.', 'warning')

    return redirect(url_for('data_entry.daily_usage'))


# ── Inventory Snapshots ─────────────────────────────────────

@data_entry_bp.route('/inventory-snapshots', methods=['GET', 'POST'])
@login_required
@admin_required
def inventory_snapshots():
    stores = Store.query.filter_by(active=True).order_by(Store.name).all()
    items = InventoryItem.query.filter_by(active=True).order_by(InventoryItem.item_name).all()

    if request.method == 'POST':
        store_id = request.form.get('store_id', type=int)
        item_id = request.form.get('item_id', type=int)
        date_str = request.form.get('snapshot_date', '').strip()
        qty_str = request.form.get('quantity_on_hand', '').strip()
        notes = request.form.get('notes', '').strip() or None

        if not store_id or not item_id or not date_str or not qty_str:
            flash('All fields except notes are required.', 'danger')
            return render_template('data_entry/inventory_snapshot.html', stores=stores, items=items)

        try:
            snapshot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('data_entry/inventory_snapshot.html', stores=stores, items=items)

        try:
            quantity = float(qty_str)
            if quantity < 0:
                raise ValueError
        except ValueError:
            flash('Quantity must be a non-negative number.', 'danger')
            return render_template('data_entry/inventory_snapshot.html', stores=stores, items=items)

        existing = InventorySnapshot.query.filter_by(
            store_id=store_id, item_id=item_id, snapshot_date=snapshot_date,
        ).first()

        if existing:
            existing.quantity_on_hand = quantity
            existing.source = 'manual'
            existing.notes = notes
        else:
            db.session.add(InventorySnapshot(
                store_id=store_id, item_id=item_id,
                snapshot_date=snapshot_date, quantity_on_hand=quantity,
                source='manual', notes=notes,
            ))

        db.session.commit()
        flash('Inventory snapshot saved.', 'success')
        return redirect(url_for('data_entry.inventory_snapshots'))

    return render_template('data_entry/inventory_snapshot.html', stores=stores, items=items)


@data_entry_bp.route('/inventory-snapshots/import', methods=['POST'])
@login_required
@admin_required
def inventory_snapshot_import():
    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a .csv file.', 'danger')
        return redirect(url_for('data_entry.inventory_snapshots'))

    content = file.read().decode('utf-8-sig')
    result = import_inventory_snapshot_csv(content)

    flash(f'Import complete: {result["imported"]} imported, {result["skipped"]} skipped.', 'success')
    if result['errors']:
        for err in result['errors'][:10]:
            flash(err, 'warning')
        if len(result['errors']) > 10:
            flash(f'...and {len(result["errors"]) - 10} more errors.', 'warning')

    return redirect(url_for('data_entry.inventory_snapshots'))
