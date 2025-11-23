"""
Quick script to fix the database schema by adding the item_type column.
"""

import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.database import RDSConnector
from sqlalchemy import text

load_dotenv()

def fix_schema():
    """Add item_type column to sales_transactions table."""

    print("=" * 70)
    print("🔧 DATABASE SCHEMA FIX")
    print("=" * 70)

    try:
        db = RDSConnector()

        print("\n✅ Connected to database")
        print(f"   Database: {db.engine.url.database}")
        print(f"   Host: {db.engine.url.host}")

        # Add the missing column
        alter_sql = """
        ALTER TABLE sales_transactions
        ADD COLUMN IF NOT EXISTS item_type VARCHAR(50);
        """

        print("\n🔨 Adding item_type column...")

        with db.engine.begin() as conn:
            conn.execute(text(alter_sql))

        print("✅ Schema updated successfully!")
        print("\n💡 You can now run: python examples/rds_sync_example.py")

        db.close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\n💡 Alternative: Drop and recreate the table")
        print("   Run this SQL in your RDS database:")
        print("   DROP TABLE sales_transactions;")
        print("\n   Then run: python examples/rds_sync_example.py")

if __name__ == "__main__":
    fix_schema()
