"""
Clear all data from Bronze, Silver, and Gold layers

Use this to start fresh before re-syncing data
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def clear_all_data():
    """Clear all synced data from database"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URL not set in .env file")
        return False

    print("=" * 70)
    print("🗑️  CLEAR ALL DATA FROM DATABASE")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will delete ALL data from Bronze, Silver, and Gold layers!")
    print()

    # Ask for confirmation
    response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    if response.lower() != 'yes':
        print("\n❌ Cancelled. No data was deleted.")
        return False

    print()
    print("🔄 Clearing data...")
    print()

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Check what exists first
        print("📊 Current data counts:")

        cursor.execute("SELECT COUNT(*) FROM bronze.square_orders")
        bronze_orders = cursor.fetchone()[0]
        print(f"   Bronze orders: {bronze_orders:,}")

        cursor.execute("SELECT COUNT(*) FROM bronze.square_line_items")
        bronze_items = cursor.fetchone()[0]
        print(f"   Bronze line items: {bronze_items:,}")

        cursor.execute("SELECT COUNT(*) FROM gold.fact_sales")
        gold_sales = cursor.fetchone()[0]
        print(f"   Gold fact_sales: {gold_sales:,}")

        print()

        # Clear Gold layer
        print("🥇 Clearing Gold layer...")
        cursor.execute("TRUNCATE TABLE gold.fact_sales CASCADE")
        cursor.execute("DELETE FROM gold.dim_customer")
        cursor.execute("DELETE FROM gold.dim_product")
        cursor.execute("DELETE FROM gold.dim_location")
        cursor.execute("DELETE FROM gold.dim_date")
        conn.commit()
        print("   ✅ Gold layer cleared")

        # Clear Silver layer
        print("🥈 Clearing Silver layer...")
        cursor.execute("DELETE FROM silver.customers")
        cursor.execute("DELETE FROM silver.products")
        cursor.execute("DELETE FROM silver.locations")
        conn.commit()
        print("   ✅ Silver layer cleared")

        # Clear Bronze layer
        print("🥉 Clearing Bronze layer...")
        cursor.execute("TRUNCATE TABLE bronze.square_orders CASCADE")
        cursor.execute("TRUNCATE TABLE bronze.square_line_items CASCADE")
        cursor.execute("DELETE FROM bronze.square_customers")
        cursor.execute("DELETE FROM bronze.square_locations")
        cursor.execute("DELETE FROM bronze.square_catalog_items")
        conn.commit()
        print("   ✅ Bronze layer cleared")

        print()
        print("=" * 70)
        print("✅ ALL DATA CLEARED SUCCESSFULLY")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Verify your .env settings:")
        print("   - SQUARE_ACCESS_TOKEN (production token)")
        print("   - SQUARE_ENVIRONMENT=production")
        print()
        print("2. Re-sync your data:")
        print("   python scripts/sync_square_to_postgres.py --days 90 --oldest")
        print()

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    clear_all_data()
