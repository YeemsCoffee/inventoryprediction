"""
Check what dates are actually stored in the database
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_dates():
    """Check dates in database"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URL not set")
        return

    print("=" * 70)
    print("🔍 CHECKING DATES IN DATABASE")
    print("=" * 70)
    print()

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Check bronze.square_orders
        print("📊 bronze.square_orders:")
        cursor.execute("""
            SELECT
                COUNT(*) as total_orders,
                MIN(created_at) as earliest_order,
                MAX(created_at) as latest_order,
                MIN(created_at::date) as earliest_date,
                MAX(created_at::date) as latest_date
            FROM bronze.square_orders
        """)
        result = cursor.fetchone()
        if result and result[0] > 0:
            print(f"   Total orders: {result[0]:,}")
            print(f"   Earliest: {result[1]} (date: {result[3]})")
            print(f"   Latest:   {result[2]} (date: {result[4]})")
        else:
            print("   No orders found")
        print()

        # Check date distribution by month
        print("📅 Orders by month:")
        cursor.execute("""
            SELECT
                TO_CHAR(created_at, 'YYYY-MM') as month,
                COUNT(*) as order_count
            FROM bronze.square_orders
            GROUP BY TO_CHAR(created_at, 'YYYY-MM')
            ORDER BY month DESC
            LIMIT 20
        """)
        months = cursor.fetchall()
        if months:
            for month, count in months:
                print(f"   {month}: {count:,} orders")
        else:
            print("   No data")
        print()

        # Check gold.fact_sales
        print("📊 gold.fact_sales:")
        cursor.execute("""
            SELECT
                COUNT(*) as total_rows,
                MIN(date_key) as earliest_date_key,
                MAX(date_key) as latest_date_key,
                MIN(order_timestamp) as earliest_timestamp,
                MAX(order_timestamp) as latest_timestamp
            FROM gold.fact_sales
        """)
        result = cursor.fetchone()
        if result and result[0] > 0:
            print(f"   Total rows: {result[0]:,}")
            print(f"   Earliest date_key: {result[1]} (timestamp: {result[3]})")
            print(f"   Latest date_key:   {result[2]} (timestamp: {result[4]})")
        else:
            print("   No sales data found")
        print()

        # Check date_key distribution
        print("📅 Sales by date_key:")
        cursor.execute("""
            SELECT
                date_key,
                COUNT(*) as row_count,
                MIN(order_timestamp::date) as actual_date
            FROM gold.fact_sales
            GROUP BY date_key
            ORDER BY date_key DESC
            LIMIT 20
        """)
        dates = cursor.fetchall()
        if dates:
            for date_key, count, actual_date in dates:
                print(f"   {date_key}: {count:,} rows (actual date: {actual_date})")
        else:
            print("   No data")

        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_dates()
