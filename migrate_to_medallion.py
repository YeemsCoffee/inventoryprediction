"""
Migrate existing sales_transactions data into Bronze layer.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.database import RDSConnector
from sqlalchemy import text
import pandas as pd


def migrate_existing_data():
    """Migrate data from sales_transactions to bronze layer."""

    print("=" * 70)
    print("📦 MIGRATING EXISTING DATA TO BRONZE LAYER")
    print("=" * 70)
    print()

    db = RDSConnector()

    # Step 1: Check existing data
    print("📋 Step 1: Checking Existing Data")
    print("-" * 70)

    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) as cnt FROM sales_transactions"))
        count = result.fetchone()[0]

    print(f"  Found {count:,} transactions in sales_transactions")
    print()

    if count == 0:
        print("  ⚠️  No data to migrate!")
        db.close()
        return

    # Step 2: Migrate to bronze
    print("📋 Step 2: Copying Data to Bronze Layer")
    print("-" * 70)

    migration_sql = """
    INSERT INTO bronze.sales_transactions (
        order_id, date, customer_id, location_id,
        product, base_product, modifiers, item_type,
        amount, price, category, variation_id,
        source_system
    )
    SELECT
        order_id,
        date,
        COALESCE(customer_id, 'Guest') as customer_id,
        location_id,
        product,
        base_product,
        modifiers,
        item_type,
        amount,
        price,
        category,
        variation_id,
        'square' as source_system
    FROM sales_transactions
    ON CONFLICT DO NOTHING
    """

    try:
        with db.engine.begin() as conn:
            result = conn.execute(text(migration_sql))
            rows_inserted = result.rowcount if hasattr(result, 'rowcount') else count

        print(f"  ✅ Migrated {rows_inserted:,} transactions to bronze layer")
    except Exception as e:
        print(f"  ❌ Migration failed: {str(e)}")
        db.close()
        return

    print()

    # Step 3: Verify
    print("📋 Step 3: Verification")
    print("-" * 70)

    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) as cnt FROM bronze.sales_transactions"))
        bronze_count = result.fetchone()[0]

    print(f"  Bronze layer now has: {bronze_count:,} transactions")
    print()

    print("=" * 70)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 70)
    print()
    print("💡 Next: Run transformations to populate Silver and Gold layers")
    print("   python transform_bronze_to_gold.py")

    db.close()


if __name__ == "__main__":
    migrate_existing_data()
