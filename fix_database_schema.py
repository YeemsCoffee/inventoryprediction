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
    """Add missing columns to sales_transactions table for modifiers support."""

    print("=" * 70)
    print("🔧 DATABASE SCHEMA FIX")
    print("=" * 70)

    try:
        db = RDSConnector()

        print("\n✅ Connected to database")
        print(f"   Database: {db.engine.url.database}")
        print(f"   Host: {db.engine.url.host}")

        # Add missing columns and update existing ones
        alter_sqls = [
            # Add item_type column if not exists
            "ALTER TABLE sales_transactions ADD COLUMN IF NOT EXISTS item_type VARCHAR(50);",
            # Add base_product column (original product name without modifiers)
            "ALTER TABLE sales_transactions ADD COLUMN IF NOT EXISTS base_product VARCHAR(255);",
            # Add modifiers column (modifier details)
            "ALTER TABLE sales_transactions ADD COLUMN IF NOT EXISTS modifiers TEXT;",
        ]

        print("\n🔨 Updating schema...")
        print("   • Adding item_type column...")
        print("   • Adding base_product column...")
        print("   • Adding modifiers column...")

        with db.engine.begin() as conn:
            for sql in alter_sqls:
                conn.execute(text(sql))

            # Try to expand product column size (may fail if data is too long)
            try:
                conn.execute(text("ALTER TABLE sales_transactions ALTER COLUMN product TYPE VARCHAR(500);"))
                print("   • Expanded product column to VARCHAR(500)")
            except Exception as e:
                print(f"   ⚠️  Could not expand product column: {str(e)}")

        # Create index on base_product for better query performance
        try:
            with db.engine.begin() as conn:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_base_product ON sales_transactions(base_product);"))
                print("   • Created index on base_product")
        except Exception:
            pass

        print("\n✅ Schema updated successfully!")
        print("\n💡 You can now run: python examples/rds_sync_example.py")
        print("   Square data will now include modifiers!")

        db.close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\n💡 Alternative: Drop and recreate the table")
        print("   Run this SQL in your RDS database:")
        print("   DROP TABLE sales_transactions;")
        print("\n   Then run: python examples/rds_sync_example.py")

if __name__ == "__main__":
    fix_schema()
