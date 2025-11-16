"""
Run database migration to add customer_id to bronze.square_orders
"""

import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def run_migration():
    """Run the customer_id migration"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in .env file")
        return

    print("🔄 Running migration: add_customer_id_to_bronze_orders")
    print()

    # Read migration SQL
    migration_path = Path(__file__).parent.parent / 'database' / 'migrations' / 'add_customer_id_to_bronze_orders.sql'
    with open(migration_path, 'r') as f:
        migration_sql = f.read()

    # Connect and execute
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    try:
        cursor.execute(migration_sql)
        conn.commit()
        print("✅ Migration completed successfully")
        print()
        print("Next step: Run the sync script")
        print("  python scripts/sync_square_to_postgres.py --days 1095")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
