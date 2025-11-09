-- ============================================================================
-- Silver Layer: Cleaned, Typed, Deduplicated Data
-- ============================================================================

-- Orders (cleaned and typed)
CREATE TABLE IF NOT EXISTS silver.orders (
    order_id VARCHAR(255) NOT NULL,
    location_id VARCHAR(255) NOT NULL,
    customer_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,
    state VARCHAR(50),

    -- Money fields (converted to decimal for precision)
    total_amount NUMERIC(12,2),
    tax_amount NUMERIC(12,2),
    discount_amount NUMERIC(12,2),
    tip_amount NUMERIC(12,2),
    currency VARCHAR(10),

    -- Derived fields (populated during insert/update)
    order_date DATE NOT NULL,
    order_hour INT,
    order_day_of_week INT,

    -- Metadata
    source_updated_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Primary key must include partition key
    PRIMARY KEY (order_id, order_date)
) PARTITION BY RANGE (order_date);

-- Create partitions for each month (automation recommended via cron)
-- Example partitions (you'll add more as needed)
CREATE TABLE IF NOT EXISTS silver.orders_2023_q1
    PARTITION OF silver.orders
    FOR VALUES FROM ('2023-01-01') TO ('2023-04-01');

CREATE TABLE IF NOT EXISTS silver.orders_2023_q2
    PARTITION OF silver.orders
    FOR VALUES FROM ('2023-04-01') TO ('2023-07-01');

CREATE TABLE IF NOT EXISTS silver.orders_2023_q3
    PARTITION OF silver.orders
    FOR VALUES FROM ('2023-07-01') TO ('2023-10-01');

CREATE TABLE IF NOT EXISTS silver.orders_2023_q4
    PARTITION OF silver.orders
    FOR VALUES FROM ('2023-10-01') TO ('2024-01-01');

CREATE TABLE IF NOT EXISTS silver.orders_2024_q1
    PARTITION OF silver.orders
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE IF NOT EXISTS silver.orders_2024_q2
    PARTITION OF silver.orders
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

CREATE TABLE IF NOT EXISTS silver.orders_2024_q3
    PARTITION OF silver.orders
    FOR VALUES FROM ('2024-07-01') TO ('2024-10-01');

CREATE TABLE IF NOT EXISTS silver.orders_2024_q4
    PARTITION OF silver.orders
    FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');

CREATE TABLE IF NOT EXISTS silver.orders_2025_q1
    PARTITION OF silver.orders
    FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');

CREATE TABLE IF NOT EXISTS silver.orders_2025_q2
    PARTITION OF silver.orders
    FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');

CREATE TABLE IF NOT EXISTS silver.orders_2025_q3
    PARTITION OF silver.orders
    FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');

CREATE TABLE IF NOT EXISTS silver.orders_2025_q4
    PARTITION OF silver.orders
    FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');

-- Indexes on parent table
CREATE INDEX IF NOT EXISTS idx_silver_orders_location ON silver.orders(location_id, order_date);
CREATE INDEX IF NOT EXISTS idx_silver_orders_customer ON silver.orders(customer_id, order_date);
CREATE INDEX IF NOT EXISTS idx_silver_orders_created ON silver.orders(created_at);

COMMENT ON TABLE silver.orders IS 'Cleaned and typed orders with partitioning by quarter';

-- Line Items (cleaned)
CREATE TABLE IF NOT EXISTS silver.line_items (
    line_item_id VARCHAR(255) PRIMARY KEY,
    order_id VARCHAR(255) NOT NULL,
    product_name VARCHAR(500) NOT NULL,
    variation_name VARCHAR(500),
    catalog_object_id VARCHAR(255),

    quantity NUMERIC(10,2) NOT NULL,
    unit_price NUMERIC(12,2),
    gross_amount NUMERIC(12,2),
    discount_amount NUMERIC(12,2),
    net_amount NUMERIC(12,2),

    -- Metadata
    processed_at TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (order_id) REFERENCES silver.orders(order_id)
);

CREATE INDEX IF NOT EXISTS idx_silver_items_order ON silver.line_items(order_id);
CREATE INDEX IF NOT EXISTS idx_silver_items_product ON silver.line_items(product_name);
CREATE INDEX IF NOT EXISTS idx_silver_items_catalog ON silver.line_items(catalog_object_id);

-- Customers (cleaned, SCD Type 2)
CREATE TABLE IF NOT EXISTS silver.customers (
    customer_sk BIGSERIAL PRIMARY KEY,  -- Surrogate key
    customer_id VARCHAR(255) NOT NULL,  -- Business key

    given_name VARCHAR(255),
    family_name VARCHAR(255),
    email_address VARCHAR(500),
    phone_number VARCHAR(100),

    -- SCD Type 2 fields
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN DEFAULT TRUE,

    -- Metadata
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_silver_customers_id ON silver.customers(customer_id, is_current);
CREATE INDEX IF NOT EXISTS idx_silver_customers_email ON silver.customers(email_address) WHERE is_current;
CREATE UNIQUE INDEX IF NOT EXISTS idx_silver_customers_current ON silver.customers(customer_id) WHERE is_current;

-- Locations (reference data)
CREATE TABLE IF NOT EXISTS silver.locations (
    location_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    address_line_1 VARCHAR(500),
    city VARCHAR(255),
    state VARCHAR(100),
    postal_code VARCHAR(50),
    country VARCHAR(10),
    status VARCHAR(50),

    -- Metadata
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Products (reference data)
CREATE TABLE IF NOT EXISTS silver.products (
    product_id VARCHAR(255) PRIMARY KEY,
    product_name VARCHAR(500) NOT NULL,
    description TEXT,
    category_id VARCHAR(255),
    category_name VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,

    -- Metadata
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_silver_products_category ON silver.products(category_id);
CREATE INDEX IF NOT EXISTS idx_silver_products_active ON silver.products(is_active);
