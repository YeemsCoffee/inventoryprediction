import os

from flask import Flask

from warehouse_app.config import config_by_name
from warehouse_app.extensions import db, migrate, login_manager, csrf


def create_app(config_name=None):
    """Application factory."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Import models so Alembic can detect them
    import warehouse_app.models  # noqa: F401

    # Register blueprints
    from warehouse_app.blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)

    from warehouse_app.blueprints.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from warehouse_app.blueprints.plans import plans_bp
    app.register_blueprint(plans_bp)

    from warehouse_app.blueprints.warehouse import warehouse_bp
    app.register_blueprint(warehouse_bp)
    csrf.exempt(warehouse_bp)  # JSON API endpoints in this blueprint

    from warehouse_app.blueprints.admin import admin_bp
    app.register_blueprint(admin_bp)

    from warehouse_app.blueprints.data_entry import data_entry_bp
    app.register_blueprint(data_entry_bp)

    return app
