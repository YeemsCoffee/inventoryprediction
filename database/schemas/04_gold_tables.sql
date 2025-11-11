-- ============================================================================
-- Gold Layer: Analytics-Ready Star Schema
-- ============================================================================

-- Dimension: Date
CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_key INTEGER PRIMARY KEY,  -- YYYYMMDD format
    date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    week_of_year INTEGER NOT NULL,
    day_of_month INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_holiday BOOLEAN DEFAULT FALSE,
    holiday_name VARCHAR(100),
    season VARCHAR(20),  -- Spring, Summer, Fall, Winter
    fiscal_year INTEGER,
    fiscal_quarter INTEGER
);

CREATE INDEX IF NOT EXISTS idx_dim_date_date ON gold.dim_date(date);
CREATE INDEX IF NOT EXISTS idx_dim_date_year_month ON gold.dim_date(year, month);

COMMENT ON TABLE gold.dim_date IS 'Date dimension table for time-based analysis';

-- Dimension: Customer (SCD Type 2)
CREATE TABLE IF NOT EXISTS gold.dim_customer (
    customer_sk BIGSERIAL PRIMARY KEY,  -- Surrogate key
    customer_id VARCHAR(255) NOT NULL,  -- Business key from Square

    given_name VARCHAR(255),
    family_name VARCHAR(255),
    full_name VARCHAR(511),  -- Populated during insert/update
    email_address VARCHAR(500),
    phone_number VARCHAR(100),

    -- Customer attributes (derived)
    first_order_date DATE,
    customer_tenure_days INTEGER,
    customer_segment VARCHAR(50),  -- High Value, Loyal, At Risk, New, etc.
    lifetime_value NUMERIC(12,2),

    -- SCD Type 2
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN DEFAULT TRUE,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_customer_id ON gold.dim_customer(customer_id, is_current);
CREATE INDEX IF NOT EXISTS idx_dim_customer_segment ON gold.dim_customer(customer_segment) WHERE is_current;
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_customer_current ON gold.dim_customer(customer_id) WHERE is_current;

COMMENT ON TABLE gold.dim_customer IS 'Customer dimension with SCD Type 2 for tracking changes over time';

-- Dimension: Product
CREATE TABLE IF NOT EXISTS gold.dim_product (
    product_sk BIGSERIAL PRIMARY KEY,
    product_id VARCHAR(255) UNIQUE NOT NULL,
    product_name VARCHAR(500) NOT NULL,
    variation_name VARCHAR(500),
    category_id VARCHAR(255),
    category_name VARCHAR(500),

    -- Product attributes
    is_active BOOLEAN DEFAULT TRUE,
    is_seasonal BOOLEAN DEFAULT FALSE,
    season VARCHAR(20),  -- If seasonal

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_product_name ON gold.dim_product(product_name);
CREATE INDEX IF NOT EXISTS idx_dim_product_category ON gold.dim_product(category_name);
CREATE INDEX IF NOT EXISTS idx_dim_product_active ON gold.dim_product(is_active);

COMMENT ON TABLE gold.dim_product IS 'Product dimension including variations and categories';

-- Dimension: Location
CREATE TABLE IF NOT EXISTS gold.dim_location (
    location_sk BIGSERIAL PRIMARY KEY,
    location_id VARCHAR(255) UNIQUE NOT NULL,
    location_name VARCHAR(500) NOT NULL,
    address_line_1 VARCHAR(500),
    city VARCHAR(255),
    state VARCHAR(100),
    postal_code VARCHAR(50),
    country VARCHAR(10),
    status VARCHAR(50),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_location_name ON gold.dim_location(location_name);

COMMENT ON TABLE gold.dim_location IS 'Location/store dimension';

-- Fact: Sales (grain: one line item per row)
CREATE TABLE IF NOT EXISTS gold.fact_sales (
    sales_sk BIGSERIAL,

    -- Dimension foreign keys
    date_key INTEGER NOT NULL,
    customer_sk BIGINT,
    product_sk BIGINT NOT NULL,
    location_sk BIGINT NOT NULL,

    -- Degenerate dimensions
    order_id VARCHAR(255) NOT NULL,
    line_item_id VARCHAR(255) NOT NULL,

    -- Measures
    quantity NUMERIC(10,2) NOT NULL,
    unit_price NUMERIC(12,2),
    gross_amount NUMERIC(12,2) NOT NULL,
    discount_amount NUMERIC(12,2) DEFAULT 0,
    net_amount NUMERIC(12,2) NOT NULL,

    -- Time
    order_timestamp TIMESTAMPTZ NOT NULL,
    order_hour INTEGER,
    order_day_of_week INTEGER,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()

    -- Note: FK constraints removed for data warehouse performance
    -- Referential integrity enforced at ETL/application level

) PARTITION BY RANGE (date_key);

-- Create partitions by year
CREATE TABLE IF NOT EXISTS gold.fact_sales_2023
    PARTITION OF gold.fact_sales
    FOR VALUES FROM (20230101) TO (20240101);

CREATE TABLE IF NOT EXISTS gold.fact_sales_2024
    PARTITION OF gold.fact_sales
    FOR VALUES FROM (20240101) TO (20250101);

CREATE TABLE IF NOT EXISTS gold.fact_sales_2025
    PARTITION OF gold.fact_sales
    FOR VALUES FROM (20250101) TO (20260101);

CREATE TABLE IF NOT EXISTS gold.fact_sales_2026
    PARTITION OF gold.fact_sales
    FOR VALUES FROM (20260101) TO (20270101);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON gold.fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON gold.fact_sales(customer_sk, date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product ON gold.fact_sales(product_sk, date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_location ON gold.fact_sales(location_sk, date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_order ON gold.fact_sales(order_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_sales_line_item ON gold.fact_sales(line_item_id, date_key);  -- Must include partition key

COMMENT ON TABLE gold.fact_sales IS 'Sales fact table with one row per line item';

-- Aggregate: Daily Sales Summary (for faster queries)
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.daily_sales_summary AS
SELECT
    date_key,
    location_sk,
    COUNT(DISTINCT order_id) as order_count,
    COUNT(DISTINCT customer_sk) as customer_count,
    SUM(quantity) as total_items,
    SUM(gross_amount) as gross_revenue,
    SUM(discount_amount) as total_discounts,
    SUM(net_amount) as net_revenue,
    AVG(net_amount) as avg_order_value
FROM gold.fact_sales
GROUP BY date_key, location_sk;

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_summary_date_loc ON gold.daily_sales_summary(date_key, location_sk);

COMMENT ON MATERIALIZED VIEW gold.daily_sales_summary IS 'Pre-aggregated daily sales metrics for performance';

-- Aggregate: Product Performance
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.product_performance AS
SELECT
    product_sk,
    date_key,
    location_sk,
    COUNT(DISTINCT order_id) as times_ordered,
    SUM(quantity) as total_quantity_sold,
    SUM(net_amount) as total_revenue,
    AVG(unit_price) as avg_unit_price,
    AVG(net_amount) as avg_revenue_per_order
FROM gold.fact_sales
GROUP BY product_sk, date_key, location_sk;

CREATE UNIQUE INDEX IF NOT EXISTS idx_product_perf_unique ON gold.product_performance(product_sk, date_key, location_sk);
CREATE INDEX IF NOT EXISTS idx_product_perf_product ON gold.product_performance(product_sk, date_key);

COMMENT ON MATERIALIZED VIEW gold.product_performance IS 'Product sales performance metrics';
