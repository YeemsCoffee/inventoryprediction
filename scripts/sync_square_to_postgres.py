"""
Direct Square API to PostgreSQL sync
Pulls all historical data from Square and loads directly into database
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.square_connector import SquareDataConnector

load_dotenv()


class SquareToPostgresSync:
    """Sync Square data directly to PostgreSQL."""

    def __init__(self, database_url: str, square_environment: str = 'production'):
        """
        Initialize syncer.

        Args:
            database_url: PostgreSQL connection string
            square_environment: 'production' or 'sandbox'
        """
        self.database_url = database_url
        self.square_environment = square_environment
        self.conn = None
        self.square = None

    def connect(self):
        """Connect to PostgreSQL and Square."""
        print("🔌 Connecting to PostgreSQL...")
        self.conn = psycopg2.connect(self.database_url)
        print("✅ Connected to PostgreSQL")
        print()

        print("🔌 Connecting to Square API...")
        self.square = SquareDataConnector(environment=self.square_environment)

        # Test connection
        test_result = self.square.test_connection()
        if test_result['success']:
            print(f"✅ Connected to Square API ({self.square_environment})")
            if test_result.get('locations'):
                print(f"   Locations: {', '.join(test_result['locations'])}")
        else:
            raise Exception(f"Failed to connect to Square: {test_result['message']}")
        print()

    def backfill_historical_data(self, days_back: int = 365):
        """
        Backfill historical data from Square.

        Args:
            days_back: Number of days of history to fetch
        """
        print("=" * 70)
        print(f"  SQUARE → POSTGRESQL HISTORICAL BACKFILL")
        print("=" * 70)
        print()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"   ({days_back} days of history)")
        print()

        # Fetch data from Square
        print("📡 Fetching data from Square API...")
        print("   This may take several minutes depending on order volume...")
        print()

        try:
            # Fetch orders and line items
            orders_df = self.square.fetch_orders(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )

            if orders_df.empty:
                print("⚠️  No orders found in date range")
                print()
                print("Possible reasons:")
                print("  - Using sandbox environment with no test data")
                print("  - Date range has no transactions")
                print("  - Square API permissions issue")
                print()
                return

            print(f"✅ Fetched {len(orders_df):,} line items from Square")
            print()

            # Load to Bronze layer
            self._load_to_bronze(orders_df)

            # Transform to Silver layer
            self._transform_to_silver(orders_df)

            # Build Gold layer
            self._build_gold_layer()

            # Summary
            self._print_summary()

            print()
            print("=" * 70)
            print("✅ BACKFILL COMPLETE!")
            print("=" * 70)
            print()
            print("Next steps:")
            print("  1. python start_production.py  # Launch dashboard")
            print("  2. Set up daily sync for ongoing updates")
            print()

        except Exception as e:
            print(f"❌ Error during backfill: {e}")
            raise

    def _load_to_bronze(self, orders_df):
        """Load raw data to Bronze layer."""
        print("📦 Loading to Bronze layer (raw data)...")

        cursor = self.conn.cursor()

        # Group line items by order to create order records
        order_groups = orders_df.groupby('order_id')

        order_values = []
        for order_id, group in order_groups:
            first_row = group.iloc[0]

            order_values.append((
                order_id,
                {},  # raw_payload (simplified since we're working from DataFrame)
                first_row.get('location_id', 'UNKNOWN'),
                first_row['date'],
                first_row['date'],
                'COMPLETED',
                int(group['price'].sum() * 100),  # Convert to cents
                'USD'
            ))

        # Insert orders
        execute_batch(cursor, """
            INSERT INTO bronze.square_orders
                (id, raw_payload, location_id, created_at, updated_at, state, total_money_amount, total_money_currency)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                updated_at = EXCLUDED.updated_at,
                total_money_amount = EXCLUDED.total_money_amount
        """, order_values)

        print(f"  ✅ Loaded {len(order_values):,} orders to bronze.square_orders")

        # Insert line items
        line_item_values = []
        for idx, row in orders_df.iterrows():
            line_item_id = f"{row['order_id']}_ITEM_{idx}"

            line_item_values.append((
                line_item_id,
                row['order_id'],
                {},  # raw_payload
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
            ON CONFLICT (uid) DO UPDATE SET
                quantity = EXCLUDED.quantity,
                total_money_amount = EXCLUDED.total_money_amount
        """, line_item_values)

        print(f"  ✅ Loaded {len(line_item_values):,} line items to bronze.square_line_items")

        self.conn.commit()
        print()

    def _transform_to_silver(self, orders_df):
        """Transform to Silver layer (cleaned data)."""
        print("🧹 Transforming to Silver layer (cleaned data)...")

        cursor = self.conn.cursor()

        # Locations
        locations = orders_df['location_id'].unique() if 'location_id' in orders_df.columns else ['LOCATION_1']

        location_values = []
        for i, loc_id in enumerate(locations):
            location_values.append((
                loc_id,
                f"Location {i+1}",
                'ACTIVE'
            ))

        execute_batch(cursor, """
            INSERT INTO silver.locations (location_id, name, status)
            VALUES (%s, %s, %s)
            ON CONFLICT (location_id) DO NOTHING
        """, location_values)

        print(f"  ✅ Loaded {len(location_values)} locations")

        # Customers
        customers = orders_df['customer_id'].unique()

        customer_values = []
        for cust_id in customers:
            first_order = orders_df[orders_df['customer_id'] == cust_id]['date'].min()

            customer_values.append((
                cust_id,
                first_order,
                True
            ))

        execute_batch(cursor, """
            INSERT INTO silver.customers (customer_id, valid_from, is_current)
            VALUES (%s, %s, %s)
            ON CONFLICT ON CONSTRAINT idx_silver_customers_current DO NOTHING
        """, customer_values)

        print(f"  ✅ Loaded {len(customer_values):,} customers")

        # Products
        products = orders_df['product'].unique()

        product_values = []
        for prod in products:
            product_id = f"PROD_{hash(prod) % 10000000}"
            product_values.append((
                product_id,
                prod,
                True
            ))

        execute_batch(cursor, """
            INSERT INTO silver.products (product_id, product_name, is_active)
            VALUES (%s, %s, %s)
            ON CONFLICT (product_id) DO NOTHING
        """, product_values)

        print(f"  ✅ Loaded {len(product_values)} products")

        self.conn.commit()
        print()

    def _build_gold_layer(self):
        """Build Gold layer (analytics star schema)."""
        print("⭐ Building Gold layer (analytics star schema)...")

        cursor = self.conn.cursor()

        # Populate dimensions from silver
        print("  🔄 Populating dimension tables...")

        # dim_customer
        cursor.execute("""
            INSERT INTO gold.dim_customer (customer_id, valid_from, is_current)
            SELECT DISTINCT
                customer_id,
                valid_from,
                is_current
            FROM silver.customers
            WHERE is_current = TRUE
            ON CONFLICT ON CONSTRAINT idx_dim_customer_current DO NOTHING
        """)

        # dim_product
        cursor.execute("""
            INSERT INTO gold.dim_product (product_id, product_name, is_active)
            SELECT DISTINCT
                product_id,
                product_name,
                is_active
            FROM silver.products
            ON CONFLICT (product_id) DO NOTHING
        """)

        # dim_location
        cursor.execute("""
            INSERT INTO gold.dim_location (location_id, location_name, status)
            SELECT
                location_id,
                name,
                status
            FROM silver.locations
            ON CONFLICT (location_id) DO NOTHING
        """)

        print("  ✅ Dimension tables populated")

        # Populate fact_sales
        print("  🔄 Populating fact_sales (this may take a while)...")

        cursor.execute("""
            INSERT INTO gold.fact_sales (
                date_key, customer_sk, product_sk, location_sk,
                order_id, line_item_id, quantity, unit_price,
                gross_amount, discount_amount, net_amount,
                order_timestamp, order_hour, order_day_of_week
            )
            SELECT
                TO_CHAR(bo.created_at, 'YYYYMMDD')::INTEGER as date_key,
                dc.customer_sk,
                dp.product_sk,
                dl.location_sk,
                bli.order_id,
                bli.uid as line_item_id,
                bli.quantity,
                bli.base_price_amount / 100.0 as unit_price,
                bli.total_money_amount / 100.0 as gross_amount,
                0 as discount_amount,
                bli.total_money_amount / 100.0 as net_amount,
                bo.created_at as order_timestamp,
                EXTRACT(HOUR FROM bo.created_at)::INTEGER as order_hour,
                EXTRACT(DOW FROM bo.created_at)::INTEGER as order_day_of_week
            FROM bronze.square_line_items bli
            JOIN bronze.square_orders bo ON bli.order_id = bo.id
            LEFT JOIN silver.customers sc ON sc.customer_id =
                COALESCE((SELECT customer_id FROM bronze.square_orders WHERE id = bli.order_id LIMIT 1), 'GUEST')
            LEFT JOIN gold.dim_customer dc ON dc.customer_id = sc.customer_id AND dc.is_current = TRUE
            LEFT JOIN silver.products sp ON sp.product_name = bli.name
            LEFT JOIN gold.dim_product dp ON dp.product_id = sp.product_id
            LEFT JOIN gold.dim_location dl ON dl.location_id = bo.location_id
            ON CONFLICT (line_item_id, date_key) DO UPDATE SET
                quantity = EXCLUDED.quantity,
                net_amount = EXCLUDED.net_amount
        """)

        rows_inserted = cursor.rowcount
        print(f"  ✅ Loaded {rows_inserted:,} rows to fact_sales")

        # Refresh materialized views
        print("  🔄 Refreshing materialized views...")

        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY gold.daily_sales_summary")
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY gold.product_performance")

        print("  ✅ Materialized views refreshed")

        self.conn.commit()
        print()

    def _print_summary(self):
        """Print migration summary."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM bronze.square_orders")
        bronze_orders = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM bronze.square_line_items")
        bronze_items = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM silver.customers WHERE is_current = TRUE")
        silver_customers = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM silver.products")
        silver_products = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM gold.fact_sales")
        gold_sales = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(order_timestamp), MAX(order_timestamp) FROM gold.fact_sales")
        date_range = cursor.fetchone()

        print("📊 SUMMARY")
        print("=" * 70)
        print(f"Bronze Layer:")
        print(f"  • Orders: {bronze_orders:,}")
        print(f"  • Line Items: {bronze_items:,}")
        print()
        print(f"Silver Layer:")
        print(f"  • Customers: {silver_customers:,}")
        print(f"  • Products: {silver_products}")
        print()
        print(f"Gold Layer:")
        print(f"  • Fact Sales Rows: {gold_sales:,}")
        if date_range[0]:
            print(f"  • Date Range: {date_range[0].strftime('%Y-%m-%d')} to {date_range[1].strftime('%Y-%m-%d')}")
        print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Sync Square data directly to PostgreSQL')
    parser.add_argument('--days', type=int, default=365,
                       help='Number of days of history to fetch (default: 365)')
    parser.add_argument('--all', action='store_true',
                       help='Fetch all available history (3 years for Square)')

    args = parser.parse_args()

    # Get configuration
    database_url = os.getenv('DATABASE_URL')
    square_env = os.getenv('SQUARE_ENVIRONMENT', 'production')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in .env file")
        sys.exit(1)

    # Determine days to fetch
    days_back = 1095 if args.all else args.days  # 3 years max for Square API

    # Run sync
    syncer = SquareToPostgresSync(database_url, square_env)

    try:
        syncer.connect()
        syncer.backfill_historical_data(days_back)
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if syncer.conn:
            syncer.conn.close()


if __name__ == "__main__":
    main()
