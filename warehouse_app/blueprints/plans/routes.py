from flask import render_template
from flask_login import login_required

from warehouse_app.blueprints.plans import plans_bp


@plans_bp.route('/')
@login_required
def index():
    # Placeholder — full implementation in Phase 3
    return render_template('plans/generate.html')
