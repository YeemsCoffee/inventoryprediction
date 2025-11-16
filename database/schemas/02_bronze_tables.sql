-- ============================================================================
-- Bronze Layer: Raw Immutable Data from Square API
-- ============================================================================

-- Orders (raw from Square)
CREATE TABLE IF NOT EXISTS bronze.square_orders (
    id VARCHAR(255) PRIMARY KEY,
    raw_payload JSONB NOT NULL,  -- Full Square API response
    location_id VARCHAR(255),
    customer_id VARCHAR(255),  -- Added for easier joins
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    state VARCHAR(50),
    total_money_amount BIGINT,  -- Amount in cents
    total_money_currency VARCHAR(10),

    -- Metadata
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    schema_version VARCHAR(20) DEFAULT 'v1',
    source VARCHAR(50) DEFAULT 'square_api'
);

-- Add customer_id column if table already exists without it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='bronze' AND table_name='square_orders' AND column_name='customer_id'
    ) THEN
        ALTER TABLE bronze.square_orders ADD COLUMN customer_id VARCHAR(255);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_bronze_orders_created ON bronze.square_orders(created_at);
CREATE INDEX IF NOT EXISTS idx_bronze_orders_location ON bronze.square_orders(location_id);
CREATE INDEX IF NOT EXISTS idx_bronze_orders_customer ON bronze.square_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_bronze_orders_ingested ON bronze.square_orders(ingested_at);

COMMENT ON TABLE bronze.square_orders IS 'Raw immutable orders from Square API';

-- Line Items (raw from Square)
CREATE TABLE IF NOT EXISTS bronze.square_line_items (
    uid VARCHAR(255) PRIMARY KEY,
    order_id VARCHAR(255) NOT NULL,
    raw_payload JSONB NOT NULL,
    name VARCHAR(500),
    quantity NUMERIC(10,2),
    base_price_amount BIGINT,
    total_money_amount BIGINT,
    catalog_object_id VARCHAR(255),
    variation_name VARCHAR(500),

    -- Metadata
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    schema_version VARCHAR(20) DEFAULT 'v1',

    FOREIGN KEY (order_id) REFERENCES bronze.square_orders(id)
);

CREATE INDEX IF NOT EXISTS idx_bronze_items_order ON bronze.square_line_items(order_id);
CREATE INDEX IF NOT EXISTS idx_bronze_items_catalog ON bronze.square_line_items(catalog_object_id);

-- Customers (raw from Square)
CREATE TABLE IF NOT EXISTS bronze.square_customers (
    id VARCHAR(255) PRIMARY KEY,
    raw_payload JSONB NOT NULL,
    given_name VARCHAR(255),
    family_name VARCHAR(255),
    email_address VARCHAR(500),
    phone_number VARCHAR(100),
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,

    -- Metadata
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    schema_version VARCHAR(20) DEFAULT 'v1'
);

CREATE INDEX IF NOT EXISTS idx_bronze_customers_email ON bronze.square_customers(email_address);
CREATE INDEX IF NOT EXISTS idx_bronze_customers_created ON bronze.square_customers(created_at);

-- Locations (raw from Square)
CREATE TABLE IF NOT EXISTS bronze.square_locations (
    id VARCHAR(255) PRIMARY KEY,
    raw_payload JSONB NOT NULL,
    name VARCHAR(500),
    address_line_1 VARCHAR(500),
    locality VARCHAR(255),
    administrative_district_level_1 VARCHAR(100),
    postal_code VARCHAR(50),
    country VARCHAR(10),
    status VARCHAR(50),

    -- Metadata
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    schema_version VARCHAR(20) DEFAULT 'v1'
);

-- Catalog Items (raw from Square)
CREATE TABLE IF NOT EXISTS bronze.square_catalog_items (
    id VARCHAR(255) PRIMARY KEY,
    raw_payload JSONB NOT NULL,
    type VARCHAR(50),
    item_name VARCHAR(500),
    description TEXT,
    category_id VARCHAR(255),
    is_deleted BOOLEAN DEFAULT FALSE,

    -- Metadata
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    schema_version VARCHAR(20) DEFAULT 'v1'
);

CREATE INDEX IF NOT EXISTS idx_bronze_catalog_category ON bronze.square_catalog_items(category_id);
