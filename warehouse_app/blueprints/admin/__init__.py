from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

from warehouse_app.blueprints.admin import routes  # noqa: F401, E402
