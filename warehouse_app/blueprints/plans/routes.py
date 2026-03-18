from datetime import date, datetime

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from warehouse_app.blueprints.plans import plans_bp
from warehouse_app.auth_helpers import admin_required
from warehouse_app.models.replenishment_plan import ReplenishmentPlan
from warehouse_app.services.plan_generation import generate_plan


@plans_bp.route('/', methods=['GET', 'POST'])
@login_required
@admin_required
def generate():
    if request.method == 'POST':
        date_str = request.form.get('plan_date', '').strip()
        regenerate = request.form.get('regenerate') == 'on'
        confirmed = request.form.get('confirmed') == 'yes'

        if not date_str:
            flash('Plan date is required.', 'danger')
            return render_template('plans/generate.html')

        try:
            plan_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('plans/generate.html')

        # Pre-flight check: warn if a plan already exists and they haven't confirmed
        existing = ReplenishmentPlan.query.filter_by(plan_date=plan_date).first()
        if existing and not confirmed:
            if not regenerate:
                flash(
                    f'A plan already exists for {plan_date} (status: {existing.status}). '
                    'Check "Regenerate" to replace a draft plan.',
                    'danger',
                )
                return render_template('plans/generate.html')
            if existing.status != 'draft':
                flash(
                    f'Cannot regenerate — the plan for {plan_date} has status '
                    f'"{existing.status}". Only draft plans can be replaced.',
                    'danger',
                )
                return render_template('plans/generate.html')
            # Show confirmation for regeneration
            return render_template('plans/generate.html',
                                   confirm_regenerate=True,
                                   plan_date=date_str)

        try:
            result = generate_plan(plan_date, current_user.id, regenerate=regenerate)
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('plans/generate.html')

        flash(f'Plan generated for {plan_date}.', 'success')
        return render_template('plans/summary.html',
                               plan=result['plan'],
                               total_lines=result['total_lines'],
                               total_stores=result['total_stores'],
                               low_confidence=result['low_confidence'],
                               warnings=result['warnings'],
                               zero_qty_skipped=result.get('zero_qty_skipped', 0))

    return render_template('plans/generate.html')
