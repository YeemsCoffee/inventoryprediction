from flask import Blueprint

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

from warehouse_app.blueprints.dashboard import routes  # noqa: F401, E402
