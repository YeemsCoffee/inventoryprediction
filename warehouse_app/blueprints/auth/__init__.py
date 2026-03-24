from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

from warehouse_app.blueprints.auth import routes  # noqa: F401, E402
