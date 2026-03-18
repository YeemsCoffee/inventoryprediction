from flask import render_template
from flask_login import login_required

from warehouse_app.blueprints.data_entry import data_entry_bp
from warehouse_app.auth_helpers import admin_required


@data_entry_bp.route('/daily-usage')
@login_required
@admin_required
def daily_usage():
    # Placeholder — full implementation in Phase 3
    return render_template('data_entry/daily_usage.html')


@data_entry_bp.route('/inventory-snapshots')
@login_required
@admin_required
def inventory_snapshots():
    # Placeholder — full implementation in Phase 3
    return render_template('data_entry/inventory_snapshot.html')
