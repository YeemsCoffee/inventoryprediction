from flask import render_template
from flask_login import login_required

from warehouse_app.blueprints.admin import admin_bp
from warehouse_app.auth_helpers import admin_required


@admin_bp.route('/stores')
@login_required
@admin_required
def stores():
    # Placeholder — full implementation in Phase 3
    return render_template('admin/stores.html')


@admin_bp.route('/items')
@login_required
@admin_required
def items():
    # Placeholder — full implementation in Phase 3
    return render_template('admin/items.html')


@admin_bp.route('/store-item-settings')
@login_required
@admin_required
def store_item_settings():
    # Placeholder — full implementation in Phase 3
    return render_template('admin/store_item_settings.html')
