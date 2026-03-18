import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # ── Session settings ──────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('SESSION_LIFETIME_SECONDS', 28800))  # 8 hours

    # ── Recommendation engine ─────────────────────────────────
    DEFAULT_USAGE_WINDOW_SHORT = 7    # days for short-term average
    DEFAULT_USAGE_WINDOW_LONG = 14    # days for long-term average
    MIN_DATA_POINTS_HIGH_CONFIDENCE = 5

    # ── CSV import limits ─────────────────────────────────────
    CSV_MAX_ROWS = 10000
    CSV_MAX_QUANTITY = 999999
    CSV_MAX_NOTE_LENGTH = 500

    # ── Fulfillment API limits ────────────────────────────────
    BULK_UPDATE_MAX_LINES = 500
    PICKER_NOTE_MAX_LENGTH = 500

    # ── Audit log ─────────────────────────────────────────────
    ACTIVITY_LOG_DEFAULT_LIMIT = 200


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, 'warehouse.db')
    )


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'TEST_DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, 'warehouse_test.db')
    )
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration — expects PostgreSQL via DATABASE_URL."""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}
