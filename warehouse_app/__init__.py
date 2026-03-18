import logging
import os
import sys

from flask import Flask, jsonify, render_template_string

from warehouse_app.config import config_by_name
from warehouse_app.extensions import db, migrate, login_manager, csrf


def _configure_logging(app):
    """Set up structured logging."""
    log_level = logging.DEBUG if app.debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)


def _register_error_handlers(app):
    """Register custom error handlers."""

    error_template = '''
    <!DOCTYPE html>
    <html><head><title>{{ title }}</title>
    <style>body{font-family:sans-serif;text-align:center;margin-top:80px;}
    h1{font-size:48px;color:#666;}p{color:#999;}</style></head>
    <body><h1>{{ code }}</h1><p>{{ message }}</p>
    <a href="/">Back to Dashboard</a></body></html>
    '''

    @app.errorhandler(401)
    def unauthorized(e):
        if _wants_json(e):
            return jsonify(error='Authentication required'), 401
        return render_template_string(error_template,
                                      title='Unauthorized', code=401,
                                      message='Please log in to access this page.'), 401

    @app.errorhandler(403)
    def forbidden(e):
        if _wants_json(e):
            return jsonify(error='Insufficient permissions'), 403
        return render_template_string(error_template,
                                      title='Forbidden', code=403,
                                      message='You do not have permission to access this resource.'), 403

    @app.errorhandler(404)
    def not_found(e):
        if _wants_json(e):
            return jsonify(error='Resource not found'), 404
        return render_template_string(error_template,
                                      title='Not Found', code=404,
                                      message='The page you requested could not be found.'), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f'Internal server error: {e}')
        if _wants_json(e):
            return jsonify(error='Internal server error'), 500
        return render_template_string(error_template,
                                      title='Server Error', code=500,
                                      message='An unexpected error occurred.'), 500


def _wants_json(error):
    """Check if the request prefers JSON response."""
    from flask import request
    return (request.accept_mimetypes.best == 'application/json' or
            request.content_type == 'application/json')


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

    # Set up logging and error handlers
    _configure_logging(app)
    _register_error_handlers(app)

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
