import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # ── Session settings ──────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('SESSION_LIFETIME_SECONDS', 28800))  # 8 hours

    # ── Forecasting engine ───────────────────────────────────
    # Supported: 'historical_simple_v1', 'historical_weighted_v1'
    # Future: 'ml_model_v1'
    FORECAST_METHOD = os.environ.get('FORECAST_METHOD', 'historical_simple_v1')
    DEFAULT_USAGE_WINDOW_SHORT = 30   # days for short-term average
    DEFAULT_USAGE_WINDOW_LONG = 60    # days for long-term average
    MIN_DATA_POINTS_HIGH_CONFIDENCE = 5

    # ── Weighted forecast settings (historical_weighted_v1) ──
    WEIGHTED_DECAY_FACTOR = float(os.environ.get('WEIGHTED_DECAY_FACTOR', '0.9'))
    WEIGHTED_DOW_MULTIPLIER = float(os.environ.get('WEIGHTED_DOW_MULTIPLIER', '0.0'))  # 0 = disabled

    # ── Multi-lane forecast routing ───────────────────────────────────
    # Lookback window (days) used to compute routing classification signals.
    # Kept separate from the forecast window so routing stays stable.
    LANE_ROUTING_WINDOW = int(os.environ.get('LANE_ROUTING_WINDOW', '28'))
    # Products with zero-rate >= this are classified as dormant (Lane 4).
    LANE_DORMANT_ZERO_RATE = float(os.environ.get('LANE_DORMANT_ZERO_RATE', '0.95'))
    # Products with zero-rate >= this (but below dormant) → intermittent (Lane 3).
    LANE_INTERMITTENT_ZERO_RATE = float(os.environ.get('LANE_INTERMITTENT_ZERO_RATE', '0.65'))
    # Delivery window (days) used to smooth periodic forecasts (Lane 2).
    LANE_PERIODIC_DELIVERY_WINDOW = int(os.environ.get('LANE_PERIODIC_DELIVERY_WINDOW', '3'))

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
