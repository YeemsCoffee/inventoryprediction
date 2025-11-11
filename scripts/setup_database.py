"""
Complete database setup script for AWS RDS PostgreSQL
Run this from your local machine where you have access to RDS
"""

import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def run_setup():
    """Set up the complete database schema"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in .env file")
        print("\nPlease add to your .env file:")
        print("DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/postgres")
        return False

    print("=" * 70)
    print("🔧 DATABASE SETUP FOR INVENTORY BI SYSTEM")
    print("=" * 70)
    print()

    try:
        # Test connection
        print("📡 Step 1: Testing database connection...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        cursor.execute("SELECT current_database(), version();")
        db_name, version = cursor.fetchone()
        print(f"✅ Connected to database: {db_name}")
        print(f"   PostgreSQL version: {version.split(',')[0]}")
        print()

        # Create schemas
        print("📦 Step 2: Creating database schemas...")
        cursor.execute("""
            CREATE SCHEMA IF NOT EXISTS bronze;
            CREATE SCHEMA IF NOT EXISTS silver;
            CREATE SCHEMA IF NOT EXISTS gold;
        """)
        conn.commit()
        print("✅ Schemas created: bronze, silver, gold")
        print()

        # Set up Bronze layer tables
        print("🥉 Step 3: Setting up Bronze layer (raw data tables)...")

        # Read and execute bronze tables SQL
        bronze_sql_path = Path(__file__).parent.parent / 'database' / 'schemas' / '02_bronze_tables.sql'
        if bronze_sql_path.exists():
            with open(bronze_sql_path, 'r') as f:
                bronze_sql = f.read()
            cursor.execute(bronze_sql)
            conn.commit()
            print("✅ Bronze layer tables created")
        else:
            print("⚠️  Bronze schema file not found, creating manually...")
            cursor.execute("""
                -- Orders (raw from Square)
                CREATE TABLE IF NOT EXISTS bronze.square_orders (
                    id VARCHAR(255) PRIMARY KEY,
                    raw_payload JSONB NOT NULL,
                    location_id VARCHAR(255),
                    customer_id VARCHAR(255),
                    created_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ,
                    state VARCHAR(50),
                    total_money_amount BIGINT,
                    total_money_currency VARCHAR(10),
                    ingested_at TIMESTAMPTZ DEFAULT NOW(),
                    schema_version VARCHAR(20) DEFAULT 'v1',
                    source VARCHAR(50) DEFAULT 'square_api'
                );

                CREATE INDEX IF NOT EXISTS idx_bronze_orders_created ON bronze.square_orders(created_at);
                CREATE INDEX IF NOT EXISTS idx_bronze_orders_location ON bronze.square_orders(location_id);
                CREATE INDEX IF NOT EXISTS idx_bronze_orders_customer ON bronze.square_orders(customer_id);
                CREATE INDEX IF NOT EXISTS idx_bronze_orders_ingested ON bronze.square_orders(ingested_at);

                -- Line Items
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
                    ingested_at TIMESTAMPTZ DEFAULT NOW(),
                    schema_version VARCHAR(20) DEFAULT 'v1',
                    FOREIGN KEY (order_id) REFERENCES bronze.square_orders(id)
                );

                CREATE INDEX IF NOT EXISTS idx_bronze_items_order ON bronze.square_line_items(order_id);
                CREATE INDEX IF NOT EXISTS idx_bronze_items_catalog ON bronze.square_line_items(catalog_object_id);

                -- Customers
                CREATE TABLE IF NOT EXISTS bronze.square_customers (
                    id VARCHAR(255) PRIMARY KEY,
                    raw_payload JSONB NOT NULL,
                    given_name VARCHAR(255),
                    family_name VARCHAR(255),
                    email_address VARCHAR(500),
                    phone_number VARCHAR(100),
                    created_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ,
                    ingested_at TIMESTAMPTZ DEFAULT NOW(),
                    schema_version VARCHAR(20) DEFAULT 'v1'
                );

                CREATE INDEX IF NOT EXISTS idx_bronze_customers_email ON bronze.square_customers(email_address);
                CREATE INDEX IF NOT EXISTS idx_bronze_customers_created ON bronze.square_customers(created_at);

                -- Locations
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
                    ingested_at TIMESTAMPTZ DEFAULT NOW(),
                    schema_version VARCHAR(20) DEFAULT 'v1'
                );

                -- Catalog Items
                CREATE TABLE IF NOT EXISTS bronze.square_catalog_items (
                    id VARCHAR(255) PRIMARY KEY,
                    raw_payload JSONB NOT NULL,
                    type VARCHAR(50),
                    item_name VARCHAR(500),
                    description TEXT,
                    category_id VARCHAR(255),
                    is_deleted BOOLEAN DEFAULT FALSE,
                    ingested_at TIMESTAMPTZ DEFAULT NOW(),
                    schema_version VARCHAR(20) DEFAULT 'v1'
                );

                CREATE INDEX IF NOT EXISTS idx_bronze_catalog_category ON bronze.square_catalog_items(category_id);
            """)
            conn.commit()
            print("✅ Bronze layer tables created manually")
        print()

        # Set up Silver layer tables
        print("🥈 Step 4: Setting up Silver layer (cleaned data tables)...")
        cursor.execute("""
            -- Cleaned sales transactions
            CREATE TABLE IF NOT EXISTS silver.sales_transactions (
                transaction_id VARCHAR(255) PRIMARY KEY,
                order_id VARCHAR(255),
                transaction_date TIMESTAMPTZ NOT NULL,
                location_id VARCHAR(255),
                customer_id VARCHAR(255),
                product_id VARCHAR(255),
                product_name VARCHAR(500),
                quantity NUMERIC(10,2) NOT NULL,
                unit_price NUMERIC(12,2),
                total_amount NUMERIC(12,2) NOT NULL,
                currency VARCHAR(10),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_silver_sales_date ON silver.sales_transactions(transaction_date);
            CREATE INDEX IF NOT EXISTS idx_silver_sales_customer ON silver.sales_transactions(customer_id);
            CREATE INDEX IF NOT EXISTS idx_silver_sales_product ON silver.sales_transactions(product_id);
        """)
        conn.commit()
        print("✅ Silver layer tables created")
        print()

        # Set up Gold layer tables
        print("🥇 Step 5: Setting up Gold layer (analytics tables)...")

        # Read and execute gold tables SQL
        gold_sql_path = Path(__file__).parent.parent / 'database' / 'schemas' / '04_gold_tables.sql'
        if gold_sql_path.exists():
            with open(gold_sql_path, 'r') as f:
                gold_sql = f.read()
            cursor.execute(gold_sql)
            conn.commit()
            print("✅ Gold layer tables created from file")
        else:
            cursor.execute("""
                -- Dimension: Customers
                CREATE TABLE IF NOT EXISTS gold.dim_customer (
                    customer_key SERIAL PRIMARY KEY,
                    customer_id VARCHAR(255) UNIQUE,
                    given_name VARCHAR(255),
                    family_name VARCHAR(255),
                    email_address VARCHAR(500),
                    phone_number VARCHAR(100),
                    customer_since TIMESTAMPTZ,
                    last_updated TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_gold_customer_id ON gold.dim_customer(customer_id);
                CREATE INDEX IF NOT EXISTS idx_gold_customer_email ON gold.dim_customer(email_address);

                -- Dimension: Products
                CREATE TABLE IF NOT EXISTS gold.dim_product (
                    product_key SERIAL PRIMARY KEY,
                    product_id VARCHAR(255) UNIQUE,
                    product_name VARCHAR(500),
                    category_id VARCHAR(255),
                    category_name VARCHAR(500),
                    is_active BOOLEAN DEFAULT TRUE,
                    last_updated TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_gold_product_id ON gold.dim_product(product_id);
                CREATE INDEX IF NOT EXISTS idx_gold_product_category ON gold.dim_product(category_id);

                -- Dimension: Locations
                CREATE TABLE IF NOT EXISTS gold.dim_location (
                    location_key SERIAL PRIMARY KEY,
                    location_id VARCHAR(255) UNIQUE,
                    location_name VARCHAR(500),
                    address_line_1 VARCHAR(500),
                    city VARCHAR(255),
                    state VARCHAR(100),
                    postal_code VARCHAR(50),
                    country VARCHAR(10),
                    last_updated TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_gold_location_id ON gold.dim_location(location_id);

                -- Dimension: Date
                CREATE TABLE IF NOT EXISTS gold.dim_date (
                    date_key INTEGER PRIMARY KEY,
                    full_date DATE NOT NULL,
                    day_of_week INTEGER,
                    day_name VARCHAR(10),
                    day_of_month INTEGER,
                    day_of_year INTEGER,
                    week_of_year INTEGER,
                    month INTEGER,
                    month_name VARCHAR(10),
                    quarter INTEGER,
                    year INTEGER,
                    is_weekend BOOLEAN,
                    is_holiday BOOLEAN DEFAULT FALSE
                );

                CREATE INDEX IF NOT EXISTS idx_gold_date_full ON gold.dim_date(full_date);

                -- Fact: Sales
                CREATE TABLE IF NOT EXISTS gold.fact_sales (
                    sales_key SERIAL PRIMARY KEY,
                    date_key INTEGER REFERENCES gold.dim_date(date_key),
                    customer_key INTEGER REFERENCES gold.dim_customer(customer_key),
                    product_key INTEGER REFERENCES gold.dim_product(product_key),
                    location_key INTEGER REFERENCES gold.dim_location(location_key),
                    order_id VARCHAR(255),
                    line_item_id VARCHAR(255),
                    quantity NUMERIC(10,2),
                    unit_price NUMERIC(12,2),
                    total_amount NUMERIC(12,2),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_gold_sales_date ON gold.fact_sales(date_key);
                CREATE INDEX IF NOT EXISTS idx_gold_sales_customer ON gold.fact_sales(customer_key);
                CREATE INDEX IF NOT EXISTS idx_gold_sales_product ON gold.fact_sales(product_key);
                CREATE INDEX IF NOT EXISTS idx_gold_sales_location ON gold.fact_sales(location_key);
                CREATE INDEX IF NOT EXISTS idx_gold_sales_order ON gold.fact_sales(order_id);
            """)
            conn.commit()
            print("✅ Gold layer tables created manually")
        print()

        # Verify customer_id column exists
        print("🔍 Step 6: Verifying customer_id column...")
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='bronze'
                AND table_name='square_orders'
                AND column_name='customer_id'
            );
        """)
        column_exists = cursor.fetchone()[0]

        if column_exists:
            print("✅ customer_id column exists in bronze.square_orders")
        else:
            print("⚠️  Adding customer_id column...")
            cursor.execute("""
                ALTER TABLE bronze.square_orders ADD COLUMN customer_id VARCHAR(255);
                CREATE INDEX IF NOT EXISTS idx_bronze_orders_customer ON bronze.square_orders(customer_id);
            """)
            conn.commit()
            print("✅ customer_id column added")
        print()

        # Summary
        print("=" * 70)
        print("✅ DATABASE SETUP COMPLETE!")
        print("=" * 70)
        print()
        print("Database is ready for data sync. Next steps:")
        print()
        print("1. Sync Square data to database:")
        print("   python scripts/sync_square_to_postgres.py --days 90 --oldest")
        print()
        print("2. Transform Bronze → Silver → Gold:")
        print("   python scripts/transform_data.py")
        print()
        print("3. Generate customer trend predictions:")
        print("   python scripts/ml_customer_trends.py")
        print()

        conn.close()
        return True

    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print()
        print("Troubleshooting steps:")
        print("1. Verify your RDS instance is running in AWS Console")
        print("2. Check security group allows your IP on port 5432")
        print("3. Verify DATABASE_URL in .env is correct")
        print("4. Check if RDS is publicly accessible (if connecting from outside VPC)")
        return False

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_setup()
