from datetime import date, datetime
from decimal import Decimal

from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from warehouse_app.blueprints.warehouse import warehouse_bp
from warehouse_app.extensions import db
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.replenishment_plan import ReplenishmentPlan
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine
from warehouse_app.models.audit_log import AuditLog
from warehouse_app.services.fulfillment import update_line_status, bulk_update_status, VALID_STATUSES


def _parse_plan_date(request):
    """Extract and validate plan_date from query params, default to today."""
    date_str = request.args.get('plan_date')
    if date_str:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    return date.today()


def _get_plan_or_404(plan_date):
    plan = ReplenishmentPlan.query.filter_by(plan_date=plan_date).first()
    if plan is None:
        abort(404)
    return plan


# ── Master Pick List ────────────────────────────────────────

@warehouse_bp.route('/pick-list')
@login_required
def master_pick_list():
    plan_date = _parse_plan_date(request)
    plan = ReplenishmentPlan.query.filter_by(plan_date=plan_date).first()

    if plan is None:
        return render_template('warehouse/master_pick_list.html',
                               plan=None, plan_date=plan_date, pick_items=[],
                               categories=[], selected_category=None, search_query='')

    # Build aggregated pick list grouped by item
    category_filter = request.args.get('category', '')
    search_query = request.args.get('q', '').strip()

    query = db.session.query(
        InventoryItem.id,
        InventoryItem.item_name,
        InventoryItem.sku,
        InventoryItem.category,
        InventoryItem.unit_of_measure,
        func.sum(ReplenishmentPlanLine.recommended_quantity).label('total_recommended'),
        func.sum(func.coalesce(ReplenishmentPlanLine.actual_quantity, 0)).label('total_actual'),
        func.count(func.distinct(ReplenishmentPlanLine.store_id)).label('store_count'),
    ).join(
        ReplenishmentPlanLine, ReplenishmentPlanLine.item_id == InventoryItem.id
    ).filter(
        ReplenishmentPlanLine.plan_id == plan.id
    ).group_by(
        InventoryItem.id,
        InventoryItem.item_name,
        InventoryItem.sku,
        InventoryItem.category,
        InventoryItem.unit_of_measure,
    )

    if category_filter:
        query = query.filter(InventoryItem.category == category_filter)

    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            db.or_(
                InventoryItem.item_name.ilike(search_pattern),
                InventoryItem.sku.ilike(search_pattern),
            )
        )

    pick_items = query.order_by(InventoryItem.category, InventoryItem.item_name).all()

    # Single query for status summary per item
    status_summary = {}
    status_rows = db.session.query(
        ReplenishmentPlanLine.item_id,
        ReplenishmentPlanLine.status,
        func.count(ReplenishmentPlanLine.id),
    ).filter(
        ReplenishmentPlanLine.plan_id == plan.id
    ).group_by(
        ReplenishmentPlanLine.item_id,
        ReplenishmentPlanLine.status,
    ).all()

    for item_id, status, count in status_rows:
        if item_id not in status_summary:
            status_summary[item_id] = {}
        status_summary[item_id][status] = count

    # Single query for store breakdown (joined to avoid N+1)
    store_breakdown = {}
    breakdown_rows = db.session.query(
        ReplenishmentPlanLine.item_id,
        Store.name,
        ReplenishmentPlanLine.recommended_quantity,
        ReplenishmentPlanLine.actual_quantity,
        ReplenishmentPlanLine.status,
    ).join(
        Store, Store.id == ReplenishmentPlanLine.store_id
    ).filter(
        ReplenishmentPlanLine.plan_id == plan.id
    ).order_by(
        ReplenishmentPlanLine.item_id, Store.name
    ).all()

    for item_id, store_name, rec_qty, act_qty, status in breakdown_rows:
        if item_id not in store_breakdown:
            store_breakdown[item_id] = []
        store_breakdown[item_id].append({
            'store_name': store_name,
            'recommended': float(rec_qty),
            'actual': float(act_qty) if act_qty is not None else None,
            'status': status,
        })

    # Categories for filter dropdown
    categories = db.session.query(
        func.distinct(InventoryItem.category)
    ).join(
        ReplenishmentPlanLine, ReplenishmentPlanLine.item_id == InventoryItem.id
    ).filter(
        ReplenishmentPlanLine.plan_id == plan.id
    ).order_by(InventoryItem.category).all()
    categories = [c[0] for c in categories]

    return render_template('warehouse/master_pick_list.html',
                           plan=plan, plan_date=plan_date,
                           pick_items=pick_items,
                           status_summary=status_summary,
                           store_breakdown=store_breakdown,
                           categories=categories,
                           selected_category=category_filter,
                           search_query=search_query)


# ── Store Delivery Sheet ────────────────────────────────────

@warehouse_bp.route('/delivery/<int:store_id>')
@login_required
def store_delivery_sheet(store_id):
    plan_date = _parse_plan_date(request)
    store = Store.query.get_or_404(store_id)
    plan = ReplenishmentPlan.query.filter_by(plan_date=plan_date).first()

    if plan is None:
        return render_template('warehouse/store_delivery_sheet.html',
                               store=store, plan=None, plan_date=plan_date,
                               lines=[], progress={})

    # Eager-load item relationship to avoid N+1 queries
    lines = ReplenishmentPlanLine.query.options(
        joinedload(ReplenishmentPlanLine.item)
    ).filter_by(
        plan_id=plan.id, store_id=store_id
    ).join(
        InventoryItem, InventoryItem.id == ReplenishmentPlanLine.item_id
    ).order_by(
        InventoryItem.category, InventoryItem.item_name
    ).all()

    # Progress summary for this store
    progress = {}
    for line in lines:
        progress[line.status] = progress.get(line.status, 0) + 1

    return render_template('warehouse/store_delivery_sheet.html',
                           store=store, plan=plan, plan_date=plan_date,
                           lines=lines, progress=progress)


# ── Exceptions / Shortages ──────────────────────────────────

@warehouse_bp.route('/exceptions')
@login_required
def exceptions():
    plan_date = _parse_plan_date(request)
    plan = ReplenishmentPlan.query.filter_by(plan_date=plan_date).first()

    if plan is None:
        return render_template('warehouse/exceptions.html',
                               plan=None, plan_date=plan_date,
                               shorted=[], low_confidence=[], warnings=[])

    # Single query with eager loading for all exception lines
    all_lines = ReplenishmentPlanLine.query.options(
        joinedload(ReplenishmentPlanLine.item),
        joinedload(ReplenishmentPlanLine.store),
    ).filter(
        ReplenishmentPlanLine.plan_id == plan.id
    ).all()

    shorted = []
    low_confidence = []
    warning_lines = []
    seen_ids = set()
    all_exceptions = []

    for line in all_lines:
        is_exception = False
        if line.status == 'shorted':
            shorted.append(line)
            is_exception = True
        if line.confidence_level == 'low':
            low_confidence.append(line)
            is_exception = True
        if line.warning_flags:
            warning_lines.append(line)
            is_exception = True
        if is_exception and line.id not in seen_ids:
            seen_ids.add(line.id)
            all_exceptions.append(line)

    return render_template('warehouse/exceptions.html',
                           plan=plan, plan_date=plan_date,
                           shorted=shorted,
                           low_confidence=low_confidence,
                           warning_lines=warning_lines,
                           all_exceptions=all_exceptions)


# ── Activity Log ────────────────────────────────────────────

@warehouse_bp.route('/activity')
@login_required
def activity_log():
    plan_date = _parse_plan_date(request)
    plan = ReplenishmentPlan.query.filter_by(plan_date=plan_date).first()

    # Show recent audit log entries for plan lines
    entries = []
    if plan:
        line_ids = [lid for (lid,) in db.session.query(
            ReplenishmentPlanLine.id
        ).filter_by(plan_id=plan.id).all()]

        if line_ids:
            entries = AuditLog.query.filter(
                AuditLog.entity_type == 'plan_line',
                AuditLog.entity_id.in_(line_ids),
            ).order_by(AuditLog.changed_at.desc()).limit(200).all()

    return render_template('warehouse/activity_log.html',
                           plan=plan, plan_date=plan_date, entries=entries)


# ── Fulfillment Update API ──────────────────────────────────

@warehouse_bp.route('/api/update-line', methods=['POST'])
@login_required
def api_update_line():
    """AJAX endpoint to update a single plan line."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    line_id = data.get('line_id')
    new_status = data.get('status')
    actual_quantity = data.get('actual_quantity')
    picker_note = data.get('picker_note')

    if not line_id:
        return jsonify({'error': 'line_id is required'}), 400

    # Validate line_id is an integer
    try:
        line_id = int(line_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'line_id must be an integer'}), 400

    # Validate status before service call
    if new_status is not None and new_status not in VALID_STATUSES:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(VALID_STATUSES)}'}), 400

    # Convert actual_quantity to float if provided
    if actual_quantity is not None:
        try:
            actual_quantity = float(actual_quantity)
            import math
            if not math.isfinite(actual_quantity):
                return jsonify({'error': 'actual_quantity must be a finite number'}), 400
            if actual_quantity < 0:
                return jsonify({'error': 'actual_quantity must be non-negative'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid actual_quantity'}), 400

    # Validate picker_note length
    if picker_note is not None and len(str(picker_note)) > 500:
        return jsonify({'error': 'picker_note must be 500 characters or fewer'}), 400

    try:
        line = update_line_status(
            line_id,
            new_status=new_status,
            actual_quantity=actual_quantity,
            picker_note=picker_note,
        )
        return jsonify({
            'success': True,
            'line_id': line.id,
            'status': line.status,
            'actual_quantity': float(line.actual_quantity) if line.actual_quantity is not None else None,
            'picker_note': line.picker_note,
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@warehouse_bp.route('/api/bulk-update', methods=['POST'])
@login_required
def api_bulk_update():
    """AJAX endpoint to bulk update line statuses."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    line_ids = data.get('line_ids', [])
    new_status = data.get('status')

    if not line_ids or not new_status:
        return jsonify({'error': 'line_ids and status are required'}), 400

    # Validate status before service call
    if new_status not in VALID_STATUSES:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(VALID_STATUSES)}'}), 400

    # Validate line_ids are all integers and cap bulk size
    if len(line_ids) > 500:
        return jsonify({'error': 'Bulk update limited to 500 lines at a time'}), 400

    try:
        line_ids = [int(lid) for lid in line_ids]
    except (ValueError, TypeError):
        return jsonify({'error': 'line_ids must be a list of integers'}), 400

    try:
        count = bulk_update_status(line_ids, new_status)
        return jsonify({'success': True, 'updated': count})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
