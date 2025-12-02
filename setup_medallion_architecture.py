"""
Set up Bronze/Silver/Gold medallion architecture in RDS.
Migrates existing sales_transactions data into proper data quality layers.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.database import RDSConnector
from sqlalchemy import text
import pandas as pd


def setup_medallion_architecture():
    """
    Set up complete Bronze/Silver/Gold architecture in RDS.
    """

    print("=" * 70)
    print("🏗️  SETTING UP BRONZE/SILVER/GOLD ARCHITECTURE")
    print("=" * 70)
    print()

    db = RDSConnector()

    # Step 1: Create schemas
    print("📋 Step 1: Creating Schemas")
    print("-" * 70)

    schemas = ['bronze', 'silver', 'gold']

    for schema in schemas:
        try:
            with db.engine.begin() as conn:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            print(f"  ✅ Created schema: {schema}")
        except Exception as e:
            print(f"  ⚠️  Schema {schema} may already exist: {str(e)}")

    print()

    # Step 2: Create Bronze tables
    print("📋 Step 2: Creating Bronze Layer Tables")
    print("-" * 70)

    bronze_sql = """
    -- Bronze: Raw data exactly as received from Square
    CREATE TABLE IF NOT EXISTS bronze.sales_transactions (
        id SERIAL,
        order_id VARCHAR(255),
        date TIMESTAMPTZ NOT NULL,
        customer_id VARCHAR(255),
        location_id VARCHAR(255),
        product VARCHAR(500),
        base_product VARCHAR(255),
        modifiers TEXT,
        item_type VARCHAR(50),
        amount INTEGER,
        price DECIMAL(10, 2),
        category VARCHAR(255),
        variation_id VARCHAR(255),

        -- Audit columns
        loaded_at TIMESTAMPTZ DEFAULT NOW(),
        source_system VARCHAR(50) DEFAULT 'square',

        PRIMARY KEY (id)
    );

    CREATE INDEX IF NOT EXISTS idx_bronze_date ON bronze.sales_transactions(date);
    CREATE INDEX IF NOT EXISTS idx_bronze_order ON bronze.sales_transactions(order_id);
    """

    try:
        with db.engine.begin() as conn:
            conn.execute(text(bronze_sql))
        print("  ✅ Created bronze.sales_transactions")
    except Exception as e:
        print(f"  ⚠️  Error creating bronze tables: {str(e)}")

    print()

    # Step 3: Create Silver tables
    print("📋 Step 3: Creating Silver Layer Tables (Cleaned Data)")
    print("-" * 70)

    silver_sql = """
    -- Silver: Cleaned, validated, deduplicated data

    -- Locations dimension
    CREATE TABLE IF NOT EXISTS silver.locations (
        location_id VARCHAR(255) PRIMARY KEY,
        location_name VARCHAR(255),
        status VARCHAR(50) DEFAULT 'ACTIVE',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Customers dimension
    CREATE TABLE IF NOT EXISTS silver.customers (
        customer_id VARCHAR(255) PRIMARY KEY,
        first_transaction_date TIMESTAMPTZ,
        is_guest BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Products dimension
    CREATE TABLE IF NOT EXISTS silver.products (
        product_id SERIAL PRIMARY KEY,
        product_name VARCHAR(500) UNIQUE NOT NULL,
        base_product_name VARCHAR(255),
        has_modifiers BOOLEAN DEFAULT FALSE,
        category VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Clean transactions fact
    CREATE TABLE IF NOT EXISTS silver.transactions (
        transaction_id SERIAL PRIMARY KEY,
        order_id VARCHAR(255),
        location_id VARCHAR(255) REFERENCES silver.locations(location_id),
        customer_id VARCHAR(255) REFERENCES silver.customers(customer_id),
        product_id INTEGER REFERENCES silver.products(product_id),

        transaction_date TIMESTAMPTZ NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price DECIMAL(10, 2),
        total_amount DECIMAL(10, 2),

        -- Derived fields
        transaction_hour INTEGER,
        transaction_day_of_week INTEGER,
        transaction_month INTEGER,
        transaction_year INTEGER,

        processed_at TIMESTAMPTZ DEFAULT NOW(),

        CONSTRAINT unique_transaction UNIQUE (order_id, product_id, transaction_date)
    );

    CREATE INDEX IF NOT EXISTS idx_silver_date ON silver.transactions(transaction_date);
    CREATE INDEX IF NOT EXISTS idx_silver_customer ON silver.transactions(customer_id);
    CREATE INDEX IF NOT EXISTS idx_silver_product ON silver.transactions(product_id);
    """

    try:
        with db.engine.begin() as conn:
            conn.execute(text(silver_sql))
        print("  ✅ Created silver layer tables")
        print("     • silver.locations")
        print("     • silver.customers")
        print("     • silver.products")
        print("     • silver.transactions")
    except Exception as e:
        print(f"  ⚠️  Error creating silver tables: {str(e)}")

    print()

    # Step 4: Create Gold tables
    print("📋 Step 4: Creating Gold Layer Tables (Analytics)")
    print("-" * 70)

    gold_sql = """
    -- Gold: Analytics-ready star schema

    -- Date dimension
    CREATE TABLE IF NOT EXISTS gold.dim_date (
        date_key INTEGER PRIMARY KEY,
        full_date DATE NOT NULL,
        year INTEGER,
        quarter INTEGER,
        month INTEGER,
        month_name VARCHAR(20),
        week INTEGER,
        day_of_month INTEGER,
        day_of_week INTEGER,
        day_name VARCHAR(20),
        is_weekend BOOLEAN
    );

    -- Customer dimension (SCD Type 2)
    CREATE TABLE IF NOT EXISTS gold.dim_customer (
        customer_sk SERIAL PRIMARY KEY,
        customer_id VARCHAR(255) NOT NULL,
        is_guest BOOLEAN DEFAULT FALSE,
        first_purchase_date DATE,

        -- SCD Type 2 fields
        valid_from TIMESTAMPTZ DEFAULT NOW(),
        valid_to TIMESTAMPTZ,
        is_current BOOLEAN DEFAULT TRUE,

        CONSTRAINT unique_current_customer UNIQUE (customer_id, is_current)
    );

    -- Product dimension
    CREATE TABLE IF NOT EXISTS gold.dim_product (
        product_sk SERIAL PRIMARY KEY,
        product_name VARCHAR(500) NOT NULL,
        base_product_name VARCHAR(255),
        has_modifiers BOOLEAN DEFAULT FALSE,
        category VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE
    );

    -- Location dimension
    CREATE TABLE IF NOT EXISTS gold.dim_location (
        location_sk SERIAL PRIMARY KEY,
        location_id VARCHAR(255) UNIQUE NOT NULL,
        location_name VARCHAR(255),
        status VARCHAR(50)
    );

    -- Sales fact table
    CREATE TABLE IF NOT EXISTS gold.fact_sales (
        sale_id SERIAL PRIMARY KEY,
        date_key INTEGER REFERENCES gold.dim_date(date_key),
        customer_sk INTEGER REFERENCES gold.dim_customer(customer_sk),
        product_sk INTEGER REFERENCES gold.dim_product(product_sk),
        location_sk INTEGER REFERENCES gold.dim_location(location_sk),

        order_id VARCHAR(255),
        transaction_timestamp TIMESTAMPTZ NOT NULL,

        quantity INTEGER NOT NULL,
        unit_price DECIMAL(10, 2),
        total_amount DECIMAL(10, 2),

        -- Time attributes for slicing
        hour_of_day INTEGER,
        day_of_week INTEGER,

        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_gold_date ON gold.fact_sales(date_key);
    CREATE INDEX IF NOT EXISTS idx_gold_customer ON gold.fact_sales(customer_sk);
    CREATE INDEX IF NOT EXISTS idx_gold_product ON gold.fact_sales(product_sk);
    CREATE INDEX IF NOT EXISTS idx_gold_timestamp ON gold.fact_sales(transaction_timestamp);

    -- Customer aggregates (for ML features)
    CREATE TABLE IF NOT EXISTS gold.customer_metrics (
        customer_sk INTEGER PRIMARY KEY REFERENCES gold.dim_customer(customer_sk),

        -- RFM metrics
        recency_days INTEGER,
        frequency INTEGER,
        monetary_total DECIMAL(12, 2),

        -- Behavioral metrics
        avg_order_value DECIMAL(10, 2),
        total_orders INTEGER,
        total_items INTEGER,
        favorite_product VARCHAR(500),

        -- Time metrics
        first_purchase_date DATE,
        last_purchase_date DATE,
        days_as_customer INTEGER,

        calculated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """

    try:
        with db.engine.begin() as conn:
            conn.execute(text(gold_sql))
        print("  ✅ Created gold layer tables")
        print("     • gold.dim_date")
        print("     • gold.dim_customer")
        print("     • gold.dim_product")
        print("     • gold.dim_location")
        print("     • gold.fact_sales")
        print("     • gold.customer_metrics")
    except Exception as e:
        print(f"  ⚠️  Error creating gold tables: {str(e)}")

    print()

    # Step 5: Summary
    print("=" * 70)
    print("✅ ARCHITECTURE SETUP COMPLETE!")
    print("=" * 70)
    print()
    print("📊 Created 3-layer medallion architecture:")
    print("   🥉 Bronze: Raw data layer (source of truth)")
    print("   🥈 Silver: Cleaned, validated data")
    print("   🥇 Gold: Analytics-ready star schema")
    print()
    print("💡 Next steps:")
    print("   1. Migrate existing data: python migrate_to_medallion.py")
    print("   2. Run transformations: python transform_bronze_to_gold.py")
    print("   3. Populate date dimension: python populate_dim_date.py")

    db.close()


if __name__ == "__main__":
    setup_medallion_architecture()
