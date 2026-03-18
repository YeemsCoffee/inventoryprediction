from datetime import date

from flask import render_template, request
from flask_login import login_required
from sqlalchemy import func

from warehouse_app.blueprints.dashboard import dashboard_bp
from warehouse_app.extensions import db
from warehouse_app.models.store import Store
from warehouse_app.models.replenishment_plan import ReplenishmentPlan
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine


@dashboard_bp.route('/')
@login_required
def index():
    plan_date_str = request.args.get('plan_date')
    if plan_date_str:
        try:
            from datetime import datetime
            plan_date = datetime.strptime(plan_date_str, '%Y-%m-%d').date()
        except ValueError:
            plan_date = date.today()
    else:
        plan_date = date.today()

    plan = ReplenishmentPlan.query.filter_by(plan_date=plan_date).first()

    stats = {
        'plan_date': plan_date,
        'plan_exists': plan is not None,
        'plan_status': plan.status if plan else None,
        'total_stores': 0,
        'total_lines': 0,
        'total_quantity': 0,
        'pending_lines': 0,
        'picked_lines': 0,
        'loaded_lines': 0,
        'delivered_lines': 0,
        'shorted_lines': 0,
    }

    if plan:
        line_stats = db.session.query(
            ReplenishmentPlanLine.status,
            func.count(ReplenishmentPlanLine.id),
            func.coalesce(func.sum(ReplenishmentPlanLine.recommended_quantity), 0),
        ).filter(
            ReplenishmentPlanLine.plan_id == plan.id,
        ).group_by(ReplenishmentPlanLine.status).all()

        for status, count, qty in line_stats:
            stats['total_lines'] += count
            stats['total_quantity'] += float(qty)
            key = f'{status}_lines'
            if key in stats:
                stats[key] = count

        store_count = db.session.query(
            func.count(func.distinct(ReplenishmentPlanLine.store_id))
        ).filter(ReplenishmentPlanLine.plan_id == plan.id).scalar()
        stats['total_stores'] = store_count

    # Get stores for delivery sheet links
    stores = []
    if plan:
        store_ids = db.session.query(
            func.distinct(ReplenishmentPlanLine.store_id)
        ).filter(ReplenishmentPlanLine.plan_id == plan.id).all()
        store_ids = [s[0] for s in store_ids]
        if store_ids:
            stores = Store.query.filter(Store.id.in_(store_ids)).order_by(Store.name).all()

    return render_template('dashboard/index.html', stats=stats, plan=plan, stores=stores)
