from flask import render_template
from flask_login import login_required

from warehouse_app.blueprints.warehouse import warehouse_bp


@warehouse_bp.route('/pick-list')
@login_required
def master_pick_list():
    # Placeholder — full implementation in Phase 4
    return render_template('warehouse/master_pick_list.html')


@warehouse_bp.route('/delivery/<int:store_id>')
@login_required
def store_delivery_sheet(store_id):
    # Placeholder — full implementation in Phase 4
    return render_template('warehouse/store_delivery_sheet.html')


@warehouse_bp.route('/exceptions')
@login_required
def exceptions():
    # Placeholder — full implementation in Phase 4
    return render_template('warehouse/exceptions.html')
