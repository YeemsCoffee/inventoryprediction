from flask import Blueprint

data_entry_bp = Blueprint('data_entry', __name__, url_prefix='/data')

from warehouse_app.blueprints.data_entry import routes  # noqa: F401, E402
