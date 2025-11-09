-- ============================================================================
-- Features Layer: ML Feature Tables
-- ============================================================================

-- Customer Daily Features (for ML models)
CREATE TABLE IF NOT EXISTS features.customer_daily_features (
    feature_date DATE NOT NULL,
    customer_sk BIGINT NOT NULL,

    -- RFM Features
    recency_days INTEGER,  -- Days since last purchase
    frequency_30d INTEGER,  -- Orders in last 30 days
    frequency_90d INTEGER,
    frequency_365d INTEGER,
    monetary_30d NUMERIC(12,2),  -- Total spent in last 30 days
    monetary_90d NUMERIC(12,2),
    monetary_365d NUMERIC(12,2),
    monetary_lifetime NUMERIC(12,2),

    -- Behavioral Features
    avg_order_value NUMERIC(12,2),
    avg_items_per_order NUMERIC(10,2),
    total_orders INTEGER,
    total_items INTEGER,
    customer_tenure_days INTEGER,

    -- Time-based Patterns
    preferred_hour INTEGER,  -- Most common hour of purchase
    preferred_day_of_week INTEGER,
    is_weekend_shopper BOOLEAN,

    -- Product Preferences
    favorite_product_sk BIGINT,
    product_diversity INTEGER,  -- Number of unique products purchased
    favorite_category VARCHAR(500),

    -- Engagement
    days_since_signup INTEGER,
    purchase_frequency NUMERIC(10,4),  -- Orders per day since signup
    is_repeat_customer BOOLEAN,

    -- Churn Indicators
    days_since_prev_order INTEGER,
    order_velocity_change NUMERIC(10,4),  -- Change in purchase frequency

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (feature_date, customer_sk)
    -- Note: FK constraint removed for data warehouse performance
) PARTITION BY RANGE (feature_date);

-- Create partitions
CREATE TABLE IF NOT EXISTS features.customer_daily_features_2023
    PARTITION OF features.customer_daily_features
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE IF NOT EXISTS features.customer_daily_features_2024
    PARTITION OF features.customer_daily_features
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE IF NOT EXISTS features.customer_daily_features_2025
    PARTITION OF features.customer_daily_features
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE INDEX IF NOT EXISTS idx_features_customer_date ON features.customer_daily_features(customer_sk, feature_date);

COMMENT ON TABLE features.customer_daily_features IS 'Point-in-time customer features for ML models';

-- Product-Location Daily Features
CREATE TABLE IF NOT EXISTS features.product_location_daily_features (
    feature_date DATE NOT NULL,
    product_sk BIGINT NOT NULL,
    location_sk BIGINT NOT NULL,

    -- Sales Features
    units_sold_1d INTEGER,
    units_sold_7d INTEGER,
    units_sold_28d INTEGER,
    units_sold_90d INTEGER,

    revenue_1d NUMERIC(12,2),
    revenue_7d NUMERIC(12,2),
    revenue_28d NUMERIC(12,2),
    revenue_90d NUMERIC(12,2),

    -- Trends
    avg_daily_units_7d NUMERIC(10,2),
    avg_daily_units_28d NUMERIC(10,2),
    units_sold_trend NUMERIC(10,4),  -- 7d vs 28d growth rate

    -- Pricing
    current_price NUMERIC(12,2),
    avg_price_28d NUMERIC(12,2),
    price_change_pct NUMERIC(10,2),

    -- Seasonality
    day_of_week INTEGER,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN,
    season VARCHAR(20),

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (feature_date, product_sk, location_sk)
    -- Note: FK constraints removed for data warehouse performance
) PARTITION BY RANGE (feature_date);

CREATE TABLE IF NOT EXISTS features.product_location_daily_features_2023
    PARTITION OF features.product_location_daily_features
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE IF NOT EXISTS features.product_location_daily_features_2024
    PARTITION OF features.product_location_daily_features
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE IF NOT EXISTS features.product_location_daily_features_2025
    PARTITION OF features.product_location_daily_features
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- ============================================================================
-- Predictions Layer: ML Model Outputs
-- ============================================================================

-- Customer Churn Predictions
CREATE TABLE IF NOT EXISTS predictions.customer_churn_scores (
    prediction_id BIGSERIAL PRIMARY KEY,
    prediction_date DATE NOT NULL,
    customer_sk BIGINT NOT NULL,

    -- Predictions
    churn_probability NUMERIC(5,4),  -- 0.0 to 1.0
    churn_risk_category VARCHAR(20),  -- Low, Medium, High
    days_until_churn INTEGER,

    -- Model metadata
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    confidence_score NUMERIC(5,4),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
    -- Note: FK constraint removed for data warehouse performance
);

CREATE INDEX IF NOT EXISTS idx_churn_customer ON predictions.customer_churn_scores(customer_sk, prediction_date);
CREATE INDEX IF NOT EXISTS idx_churn_risk ON predictions.customer_churn_scores(churn_risk_category, prediction_date);

COMMENT ON TABLE predictions.customer_churn_scores IS 'Customer churn risk predictions';

-- Demand Forecasts
CREATE TABLE IF NOT EXISTS predictions.demand_forecasts (
    forecast_id BIGSERIAL PRIMARY KEY,
    forecast_date DATE NOT NULL,  -- Date of forecast
    target_date DATE NOT NULL,  -- Date being forecast
    product_sk BIGINT NOT NULL,
    location_sk BIGINT NOT NULL,

    -- Forecast
    predicted_units NUMERIC(10,2),
    predicted_revenue NUMERIC(12,2),
    prediction_lower_bound NUMERIC(10,2),  -- 95% confidence interval
    prediction_upper_bound NUMERIC(10,2),

    -- Model metadata
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    model_accuracy NUMERIC(5,4),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
    -- Note: FK constraints removed for data warehouse performance
);

CREATE INDEX IF NOT EXISTS idx_forecast_product_date ON predictions.demand_forecasts(product_sk, target_date);
CREATE INDEX IF NOT EXISTS idx_forecast_location_date ON predictions.demand_forecasts(location_sk, target_date);

COMMENT ON TABLE predictions.demand_forecasts IS 'Demand forecasting predictions by product and location';

-- Customer Lifetime Value Predictions
CREATE TABLE IF NOT EXISTS predictions.customer_ltv_scores (
    prediction_id BIGSERIAL PRIMARY KEY,
    prediction_date DATE NOT NULL,
    customer_sk BIGINT NOT NULL,

    -- LTV Predictions
    predicted_ltv_30d NUMERIC(12,2),
    predicted_ltv_90d NUMERIC(12,2),
    predicted_ltv_365d NUMERIC(12,2),
    predicted_ltv_lifetime NUMERIC(12,2),

    -- Segmentation
    value_segment VARCHAR(50),  -- High Value, Medium Value, Low Value

    -- Model metadata
    model_name VARCHAR(100),
    model_version VARCHAR(50),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
    -- Note: FK constraint removed for data warehouse performance
);

CREATE INDEX IF NOT EXISTS idx_ltv_customer ON predictions.customer_ltv_scores(customer_sk, prediction_date);
CREATE INDEX IF NOT EXISTS idx_ltv_segment ON predictions.customer_ltv_scores(value_segment, prediction_date);

-- ============================================================================
-- Metadata Layer: System Tables
-- ============================================================================

-- Sync Log (track data pipeline runs)
CREATE TABLE IF NOT EXISTS metadata.sync_log (
    sync_id BIGSERIAL PRIMARY KEY,
    sync_name VARCHAR(200) NOT NULL,  -- e.g., 'square_orders_incremental'
    sync_type VARCHAR(50),  -- 'incremental', 'full', 'backfill'

    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    status VARCHAR(50),  -- 'running', 'success', 'failed'

    records_processed INTEGER,
    records_inserted INTEGER,
    records_updated INTEGER,
    records_failed INTEGER,

    error_message TEXT,

    -- Watermark tracking
    last_processed_timestamp TIMESTAMPTZ,
    next_start_timestamp TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sync_log_name_time ON metadata.sync_log(sync_name, start_time);
CREATE INDEX IF NOT EXISTS idx_sync_log_status ON metadata.sync_log(status, start_time);

COMMENT ON TABLE metadata.sync_log IS 'Track all data pipeline sync operations';

-- Data Quality Results
CREATE TABLE IF NOT EXISTS metadata.data_quality_results (
    test_id BIGSERIAL PRIMARY KEY,
    test_name VARCHAR(200) NOT NULL,
    table_name VARCHAR(200) NOT NULL,
    test_type VARCHAR(100),  -- 'row_count', 'null_check', 'uniqueness', etc.

    test_timestamp TIMESTAMPTZ NOT NULL,
    passed BOOLEAN NOT NULL,

    expected_value TEXT,
    actual_value TEXT,

    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dq_table_time ON metadata.data_quality_results(table_name, test_timestamp);
CREATE INDEX IF NOT EXISTS idx_dq_passed ON metadata.data_quality_results(passed, test_timestamp);

COMMENT ON TABLE metadata.data_quality_results IS 'Data quality test results';
