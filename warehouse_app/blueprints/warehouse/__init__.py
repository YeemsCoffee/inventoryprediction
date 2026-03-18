from flask import Blueprint

warehouse_bp = Blueprint('warehouse', __name__, url_prefix='/warehouse')

from warehouse_app.blueprints.warehouse import routes  # noqa: F401, E402
