from flask import Blueprint

plans_bp = Blueprint('plans', __name__, url_prefix='/plans')

from warehouse_app.blueprints.plans import routes  # noqa: F401, E402
