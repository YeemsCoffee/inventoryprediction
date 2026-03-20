import math
from datetime import datetime, date

from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from sqlalchemy import func

from warehouse_app.blueprints.data_entry import data_entry_bp
from warehouse_app.auth_helpers import admin_required
from warehouse_app.extensions import db
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot
from warehouse_app.models.actual_order import ActualOrder
from warehouse_app.models.replenishment_plan import ReplenishmentPlan
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine
from warehouse_app.services.csv_import import (
    import_daily_usage_csv,
    import_inventory_snapshot_csv,
    import_actual_orders_csv,
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
            max_qty = current_app.config.get('CSV_MAX_QUANTITY', 999999)
            if not math.isfinite(quantity) or quantity < 0 or quantity > max_qty:
                raise ValueError
        except ValueError:
            flash('Quantity must be a non-negative number (max 999,999).', 'danger')
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
            max_qty = current_app.config.get('CSV_MAX_QUANTITY', 999999)
            if not math.isfinite(quantity) or quantity < 0 or quantity > max_qty:
                raise ValueError
        except ValueError:
            flash('Quantity must be a non-negative number (max 999,999).', 'danger')
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


# ── Actual Orders ───────────────────────────────────────────

@data_entry_bp.route('/actual-orders', methods=['GET', 'POST'])
@login_required
@admin_required
def actual_orders():
    stores = Store.query.filter_by(active=True).order_by(Store.name).all()
    items = InventoryItem.query.filter_by(active=True).order_by(InventoryItem.item_name).all()

    if request.method == 'POST':
        store_id = request.form.get('store_id', type=int)
        item_id = request.form.get('item_id', type=int)
        date_str = request.form.get('order_date', '').strip()
        qty_str = request.form.get('quantity_ordered', '').strip()
        notes = request.form.get('notes', '').strip() or None

        if not store_id or not item_id or not date_str or not qty_str:
            flash('All fields except notes are required.', 'danger')
            return render_template('data_entry/actual_orders.html', stores=stores, items=items)

        try:
            order_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('data_entry/actual_orders.html', stores=stores, items=items)

        try:
            quantity = float(qty_str)
            max_qty = current_app.config.get('CSV_MAX_QUANTITY', 999999)
            if not math.isfinite(quantity) or quantity < 0 or quantity > max_qty:
                raise ValueError
        except ValueError:
            flash('Quantity must be a non-negative number (max 999,999).', 'danger')
            return render_template('data_entry/actual_orders.html', stores=stores, items=items)

        existing = ActualOrder.query.filter_by(
            store_id=store_id, item_id=item_id, order_date=order_date,
        ).first()

        if existing:
            existing.quantity_ordered = quantity
            existing.source = 'manual'
            existing.notes = notes
        else:
            db.session.add(ActualOrder(
                store_id=store_id, item_id=item_id,
                order_date=order_date, quantity_ordered=quantity,
                source='manual', notes=notes,
            ))

        db.session.commit()
        flash('Actual order saved.', 'success')
        return redirect(url_for('data_entry.actual_orders'))

    return render_template('data_entry/actual_orders.html', stores=stores, items=items)


@data_entry_bp.route('/actual-orders/import', methods=['POST'])
@login_required
@admin_required
def actual_orders_import():
    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a .csv file.', 'danger')
        return redirect(url_for('data_entry.actual_orders'))

    content = file.read().decode('utf-8-sig')
    result = import_actual_orders_csv(content)

    flash(f'Import complete: {result["imported"]} imported, {result["skipped"]} skipped.', 'success')
    if result['errors']:
        for err in result['errors'][:10]:
            flash(err, 'warning')
        if len(result['errors']) > 10:
            flash(f'...and {len(result["errors"]) - 10} more errors.', 'warning')

    return redirect(url_for('data_entry.actual_orders'))


# ── Prediction Accuracy ─────────────────────────────────────

@data_entry_bp.route('/prediction-accuracy')
@login_required
@admin_required
def prediction_accuracy():
    """Compare predicted recommendations vs actual store orders."""
    date_str = request.args.get('plan_date')
    if date_str:
        try:
            plan_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            plan_date = date.today()
    else:
        plan_date = date.today()

    plan = ReplenishmentPlan.query.filter_by(plan_date=plan_date).first()

    comparisons = []
    summary = {
        'total_lines': 0,
        'matched_lines': 0,
        'over_predicted': 0,
        'under_predicted': 0,
        'no_actual': 0,
        'total_predicted_qty': 0,
        'total_actual_qty': 0,
        'total_abs_error': 0,
    }

    if plan:
        lines = ReplenishmentPlanLine.query.filter_by(plan_id=plan.id).all()

        for line in lines:
            actual = ActualOrder.query.filter_by(
                store_id=line.store_id,
                item_id=line.item_id,
                order_date=plan_date,
            ).first()

            predicted = float(line.recommended_quantity)
            actual_qty = float(actual.quantity_ordered) if actual else None

            diff = None
            pct_error = None
            status = 'no_actual'

            if actual_qty is not None:
                diff = actual_qty - predicted
                if actual_qty > 0:
                    pct_error = abs(diff) / actual_qty * 100
                elif predicted > 0:
                    pct_error = 100.0

                if abs(diff) < 0.01:
                    status = 'match'
                    summary['matched_lines'] += 1
                elif diff > 0:
                    status = 'under'
                    summary['under_predicted'] += 1
                else:
                    status = 'over'
                    summary['over_predicted'] += 1

                summary['total_actual_qty'] += actual_qty
                summary['total_abs_error'] += abs(diff)
            else:
                summary['no_actual'] += 1

            summary['total_lines'] += 1
            summary['total_predicted_qty'] += predicted

            comparisons.append({
                'store': line.store,
                'item': line.item,
                'predicted': predicted,
                'actual': actual_qty,
                'diff': diff,
                'pct_error': pct_error,
                'status': status,
                'confidence': line.confidence_level,
            })

    # Sort: mismatches first, then by absolute difference
    comparisons.sort(key=lambda c: (
        c['status'] == 'no_actual',
        c['status'] == 'match',
        -(abs(c['diff']) if c['diff'] is not None else 0),
    ))

    if summary['total_actual_qty'] > 0:
        summary['wmape'] = summary['total_abs_error'] / summary['total_actual_qty'] * 100
    else:
        summary['wmape'] = None

    return render_template(
        'data_entry/prediction_accuracy.html',
        plan_date=plan_date,
        plan=plan,
        comparisons=comparisons,
        summary=summary,
    )
