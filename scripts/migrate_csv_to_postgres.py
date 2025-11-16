"""
Migrate CSV data to PostgreSQL
One-time migration script to load historical data from CSV into PostgreSQL
"""

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


class CSVToPostgresMigrator:
    """Migrate CSV data to PostgreSQL database."""

    def __init__(self, database_url: str, csv_path: str):
        """
        Initialize migrator.

        Args:
            database_url: PostgreSQL connection string
            csv_path: Path to CSV file with sales data
        """
        self.database_url = database_url
        self.csv_path = csv_path
        self.conn = None

    def connect(self):
        """Connect to PostgreSQL."""
        print("🔌 Connecting to PostgreSQL...")
        self.conn = psycopg2.connect(self.database_url)
        print("✅ Connected")
        print()

    def load_csv(self) -> pd.DataFrame:
        """Load and prepare CSV data."""
        print(f"📂 Loading CSV from: {self.csv_path}")

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        # Load CSV
        df = pd.read_csv(self.csv_path)
        print(f"✅ Loaded {len(df):,} rows from CSV")
        print()

        # Parse dates
        df['date'] = pd.to_datetime(df['date'], format='ISO8601')

        return df

    def migrate_bronze_layer(self, df: pd.DataFrame):
        """Migrate to bronze layer (raw data)."""
        print("📦 Migrating to Bronze layer...")

        cursor = self.conn.cursor()

        # Since CSV doesn't have full Square order structure,
        # we'll create synthetic orders from line items

        # Group by date, customer, location to create orders
        orders = df.groupby(['date', 'customer_id', 'location_id']).agg({
            'price': 'sum',
            'amount': 'sum'
        }).reset_index()

        orders['order_id'] = orders.apply(
            lambda x: f"ORDER_{x.name}_{x['customer_id']}",
            axis=1
        )

        # Insert orders
        order_values = []
        for _, row in orders.iterrows():
            order_values.append((
                row['order_id'],
                {},  # Empty JSONB for raw_payload (since we don't have full Square data)
                row.get('location_id', 'LOC_001'),
                row['date'],
                row['date'],
                'COMPLETED',
                int(row['price'] * 100),  # Convert to cents
                'USD'
            ))

        execute_batch(cursor, """
            INSERT INTO bronze.square_orders
                (id, raw_payload, location_id, created_at, updated_at, state, total_money_amount, total_money_currency)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, order_values)

        print(f"  ✅ Migrated {len(order_values):,} orders to bronze.square_orders")

        # Insert line items
        df['line_item_id'] = df.apply(
            lambda x: f"ITEM_{x.name}",
            axis=1
        )

        df['order_id'] = df.apply(
            lambda x: f"ORDER_{orders[(orders['date'] == x['date']) & (orders['customer_id'] == x['customer_id'])].index[0]}_{x['customer_id']}",
            axis=1
        )

        line_item_values = []
        for _, row in df.iterrows():
            line_item_values.append((
                row['line_item_id'],
                row['order_id'],
                {},  # Empty JSONB
                row['product'],
                row['amount'],
                int((row['price'] / row['amount']) * 100) if row['amount'] > 0 else 0,
                int(row['price'] * 100),
                row.get('catalog_object_id', None),
                row.get('variation_name', None)
            ))

        execute_batch(cursor, """
            INSERT INTO bronze.square_line_items
                (uid, order_id, raw_payload, name, quantity, base_price_amount, total_money_amount, catalog_object_id, variation_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (uid) DO NOTHING
        """, line_item_values)

        print(f"  ✅ Migrated {len(line_item_values):,} line items to bronze.square_line_items")

        self.conn.commit()
        print()

    def migrate_silver_layer(self, df: pd.DataFrame):
        """Migrate to silver layer (cleaned data)."""
        print("🧹 Migrating to Silver layer...")

        cursor = self.conn.cursor()

        # Unique locations
        locations = df['location_id'].unique() if 'location_id' in df.columns else ['LOC_001', 'LOC_002']

        location_values = []
        for i, loc_id in enumerate(locations):
            location_values.append((
                loc_id,
                f"Location {i+1}",
                None, None, None, None, None,
                'ACTIVE'
            ))

        execute_batch(cursor, """
            INSERT INTO silver.locations
                (location_id, name, address_line_1, city, state, postal_code, country, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (location_id) DO NOTHING
        """, location_values)

        print(f"  ✅ Migrated {len(location_values)} locations")

        # Unique customers
        customers = df['customer_id'].unique()

        customer_values = []
        for cust_id in customers:
            cust_data = df[df['customer_id'] == cust_id].iloc[0]
            first_order = df[df['customer_id'] == cust_id]['date'].min()

            customer_values.append((
                1,  # customer_sk (will be assigned by DB)
                cust_id,
                None, None, None, None,  # No name/email in CSV
                first_order,
                None,
                True
            ))

        execute_batch(cursor, """
            INSERT INTO silver.customers
                (customer_sk, customer_id, given_name, family_name, email_address, phone_number, valid_from, valid_to, is_current)
            VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT idx_silver_customers_current DO NOTHING
        """, customer_values)

        print(f"  ✅ Migrated {len(customer_values):,} customers")

        # Unique products
        products = df['product'].unique()

        product_values = []
        for prod in products:
            product_values.append((
                f"PROD_{hash(prod) % 10000000}",
                prod,
                None, None, None,
                True
            ))

        execute_batch(cursor, """
            INSERT INTO silver.products
                (product_id, product_name, description, category_id, category_name, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id) DO NOTHING
        """, product_values)

        print(f"  ✅ Migrated {len(product_values)} products")

        self.conn.commit()
        print()

    def migrate_gold_layer(self, df: pd.DataFrame):
        """Migrate to gold layer (analytics-ready star schema)."""
        print("⭐ Migrating to Gold layer...")

        cursor = self.conn.cursor()

        # First, populate dim tables and get surrogate keys

        # Populate dim_customer
        cursor.execute("""
            INSERT INTO gold.dim_customer (customer_id, given_name, family_name, valid_from, is_current)
            SELECT DISTINCT
                customer_id,
                NULL as given_name,
                NULL as family_name,
                MIN(valid_from) OVER (PARTITION BY customer_id) as valid_from,
                TRUE
            FROM silver.customers
            WHERE is_current = TRUE
            ON CONFLICT ON CONSTRAINT idx_dim_customer_current DO NOTHING
        """)

        # Populate dim_product
        cursor.execute("""
            INSERT INTO gold.dim_product (product_id, product_name, category_name, is_active)
            SELECT DISTINCT
                product_id,
                product_name,
                category_name,
                is_active
            FROM silver.products
            ON CONFLICT (product_id) DO NOTHING
        """)

        # Populate dim_location
        cursor.execute("""
            INSERT INTO gold.dim_location (location_id, location_name, status)
            SELECT
                location_id,
                name,
                status
            FROM silver.locations
            ON CONFLICT (location_id) DO NOTHING
        """)

        print("  ✅ Populated dimension tables")

        # Now populate fact_sales
        # This is complex - we need to join to get surrogate keys

        print("  🔄 Populating fact_sales (this may take a while)...")

        # Build fact table from CSV
        fact_data = []
        for _, row in df.iterrows():
            order_date = row['date'].date()
            date_key = int(order_date.strftime('%Y%m%d'))

            fact_data.append({
                'date_key': date_key,
                'customer_id': row['customer_id'],
                'product_name': row['product'],
                'location_id': row.get('location_id', 'LOC_001'),
                'order_id': f"ORDER_{row.name}",
                'line_item_id': f"ITEM_{row.name}",
                'quantity': row['amount'],
                'unit_price': row['price'] / row['amount'] if row['amount'] > 0 else 0,
                'gross_amount': row['price'],
                'discount_amount': 0,
                'net_amount': row['price'],
                'order_timestamp': row['date'],
                'order_hour': row['date'].hour,
                'order_day_of_week': row['date'].dayofweek
            })

        # Insert in batches
        batch_size = 1000
        total_inserted = 0

        for i in range(0, len(fact_data), batch_size):
            batch = fact_data[i:i+batch_size]

            values = []
            for record in batch:
                values.append((
                    record['date_key'],
                    record['customer_id'],
                    record['product_name'],
                    record['location_id'],
                    record['order_id'],
                    record['line_item_id'],
                    record['quantity'],
                    record['unit_price'],
                    record['gross_amount'],
                    record['discount_amount'],
                    record['net_amount'],
                    record['order_timestamp'],
                    record['order_hour'],
                    record['order_day_of_week']
                ))

            execute_batch(cursor, """
                INSERT INTO gold.fact_sales (
                    date_key, customer_sk, product_sk, location_sk,
                    order_id, line_item_id, quantity, unit_price,
                    gross_amount, discount_amount, net_amount,
                    order_timestamp, order_hour, order_day_of_week
                )
                SELECT
                    %s as date_key,
                    c.customer_sk,
                    p.product_sk,
                    l.location_sk,
                    %s as order_id,
                    %s as line_item_id,
                    %s as quantity,
                    %s as unit_price,
                    %s as gross_amount,
                    %s as discount_amount,
                    %s as net_amount,
                    %s as order_timestamp,
                    %s as order_hour,
                    %s as order_day_of_week
                FROM gold.dim_customer c
                CROSS JOIN gold.dim_product p
                CROSS JOIN gold.dim_location l
                WHERE c.customer_id = %s
                  AND p.product_name = %s
                  AND l.location_id = %s
                  AND c.is_current = TRUE
                ON CONFLICT (line_item_id) DO NOTHING
            """, [(v + (v[1], v[2], v[3])) for v in values])

            total_inserted += len(batch)
            if (i + batch_size) % 10000 == 0:
                print(f"    ⏳ Processed {total_inserted:,} / {len(fact_data):,} rows...")

        print(f"  ✅ Migrated {len(fact_data):,} rows to fact_sales")

        self.conn.commit()
        print()

    def refresh_materialized_views(self):
        """Refresh materialized views."""
        print("🔄 Refreshing materialized views...")

        cursor = self.conn.cursor()

        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY gold.daily_sales_summary")
        print("  ✅ Refreshed daily_sales_summary")

        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY gold.product_performance")
        print("  ✅ Refreshed product_performance")

        self.conn.commit()
        print()

    def run_migration(self):
        """Run complete migration."""
        start_time = datetime.now()

        print("=" * 70)
        print("  CSV to PostgreSQL Migration")
        print("=" * 70)
        print()

        try:
            # Connect
            self.connect()

            # Load CSV
            df = self.load_csv()

            # Migrate layers
            self.migrate_bronze_layer(df)
            self.migrate_silver_layer(df)
            self.migrate_gold_layer(df)

            # Refresh views
            self.refresh_materialized_views()

            # Summary
            cursor = self.conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM bronze.square_orders")
            bronze_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM silver.customers WHERE is_current = TRUE")
            customer_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM gold.fact_sales")
            fact_count = cursor.fetchone()[0]

            elapsed = datetime.now() - start_time

            print("=" * 70)
            print("✅ Migration Complete!")
            print("=" * 70)
            print()
            print(f"📊 Summary:")
            print(f"  • Bronze orders: {bronze_count:,}")
            print(f"  • Silver customers: {customer_count:,}")
            print(f"  • Gold fact_sales: {fact_count:,}")
            print(f"  • Time elapsed: {elapsed}")
            print()
            print("Next steps:")
            print("  1. Set up incremental sync: python scripts/sync_square_to_postgres.py")
            print("  2. Run dbt transformations: dbt run")
            print("  3. Update dashboard: python start_production.py")
            print()

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            if self.conn:
                self.conn.rollback()
            raise

        finally:
            if self.conn:
                self.conn.close()


def main():
    # Get configuration
    database_url = os.getenv('DATABASE_URL')
    csv_path = os.getenv('CSV_DATA_PATH', 'data/raw/square_sales.csv')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        print("Add to .env file: DATABASE_URL=postgresql://user:password@localhost:5432/inventory_bi")
        sys.exit(1)

    # Run migration
    migrator = CSVToPostgresMigrator(database_url, csv_path)
    migrator.run_migration()


if __name__ == "__main__":
    main()
