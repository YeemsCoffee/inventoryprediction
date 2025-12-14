"""
Transform data through Bronze → Silver → Gold layers.
Complete ETL pipeline for data quality and analytics.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.database import RDSConnector
from sqlalchemy import text
import pandas as pd


def transform_bronze_to_silver(db):
    """Transform bronze to silver (clean and validate)."""

    print("=" * 70)
    print("🥈 BRONZE → SILVER TRANSFORMATION")
    print("=" * 70)
    print()

    # 1. Populate silver.locations
    print("📋 Populating silver.locations...")

    sql = """
    INSERT INTO silver.locations (location_id, name, status)
    SELECT DISTINCT
        location_id,
        'Location ' || location_id as name,
        'ACTIVE' as status
    FROM bronze.sales_transactions
    WHERE location_id IS NOT NULL
    ON CONFLICT (location_id) DO NOTHING
    """

    with db.engine.begin() as conn:
        result = conn.execute(text(sql))
        print(f"  ✅ Loaded {result.rowcount if hasattr(result, 'rowcount') else '?'} locations")

    # 2. Populate silver.customers
    print("📋 Populating silver.customers...")

    sql = """
    INSERT INTO silver.customers (customer_id, valid_from, is_current)
    SELECT
        customer_id,
        MIN(date) as valid_from,
        TRUE as is_current
    FROM bronze.sales_transactions
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
    ON CONFLICT (customer_id) WHERE is_current DO NOTHING
    """

    with db.engine.begin() as conn:
        result = conn.execute(text(sql))
        print(f"  ✅ Loaded {result.rowcount if hasattr(result, 'rowcount') else '?'} customers")

    # 3. Populate silver.products
    print("📋 Populating silver.products...")

    sql = """
    INSERT INTO silver.products (
        product_name, base_product_name, has_modifiers, category, is_active
    )
    SELECT DISTINCT
        product as product_name,
        COALESCE(base_product, product) as base_product_name,
        (modifiers IS NOT NULL AND modifiers != '') as has_modifiers,
        category,
        TRUE as is_active
    FROM bronze.sales_transactions
    WHERE product IS NOT NULL AND product != ''
    ON CONFLICT (product_name) DO NOTHING
    """

    with db.engine.begin() as conn:
        result = conn.execute(text(sql))
        print(f"  ✅ Loaded {result.rowcount if hasattr(result, 'rowcount') else '?'} products")

    # 4. Populate silver.transactions
    print("📋 Populating silver.transactions...")

    sql = """
    INSERT INTO silver.transactions (
        order_id, location_id, customer_id, product_id,
        transaction_date, quantity, unit_price, total_amount,
        transaction_hour, transaction_day_of_week,
        transaction_month, transaction_year
    )
    SELECT
        b.order_id,
        b.location_id,
        b.customer_id,
        p.product_id,
        b.date as transaction_date,
        b.amount as quantity,
        b.price / NULLIF(b.amount, 0) as unit_price,
        b.price as total_amount,
        EXTRACT(HOUR FROM b.date) as transaction_hour,
        EXTRACT(DOW FROM b.date) as transaction_day_of_week,
        EXTRACT(MONTH FROM b.date) as transaction_month,
        EXTRACT(YEAR FROM b.date) as transaction_year
    FROM bronze.sales_transactions b
    JOIN silver.products p ON b.product = p.product_name
    WHERE b.amount > 0
    ON CONFLICT (order_id, product_id, transaction_date) DO NOTHING
    """

    with db.engine.begin() as conn:
        result = conn.execute(text(sql))
        print(f"  ✅ Loaded {result.rowcount if hasattr(result, 'rowcount') else '?'} transactions")

    print()


def transform_silver_to_gold(db):
    """Transform silver to gold (analytics star schema)."""

    print("=" * 70)
    print("🥇 SILVER → GOLD TRANSFORMATION")
    print("=" * 70)
    print()

    # 1. Populate gold.dim_customer
    print("📋 Populating gold.dim_customer...")

    sql = """
    INSERT INTO gold.dim_customer (
        customer_id, is_guest, first_purchase_date, valid_from, is_current
    )
    SELECT
        customer_id,
        is_guest,
        DATE(first_transaction_date) as first_purchase_date,
        first_transaction_date as valid_from,
        TRUE as is_current
    FROM silver.customers
    ON CONFLICT (customer_id, is_current) DO NOTHING
    """

    with db.engine.begin() as conn:
        result = conn.execute(text(sql))
        print(f"  ✅ Loaded {result.rowcount if hasattr(result, 'rowcount') else '?'} customers")

    # 2. Populate gold.dim_product
    print("📋 Populating gold.dim_product...")

    sql = """
    INSERT INTO gold.dim_product (
        product_name, base_product_name, has_modifiers, category, is_active
    )
    SELECT
        product_name,
        base_product_name,
        has_modifiers,
        category,
        is_active
    FROM silver.products
    ON CONFLICT DO NOTHING
    """

    with db.engine.begin() as conn:
        result = conn.execute(text(sql))
        print(f"  ✅ Loaded {result.rowcount if hasattr(result, 'rowcount') else '?'} products")

    # 3. Populate gold.dim_location
    print("📋 Populating gold.dim_location...")

    sql = """
    INSERT INTO gold.dim_location (
        location_id,
        location_name,
        address_line_1,
        city,
        state,
        postal_code,
        country,
        status
    )
    SELECT
        location_id,
        name as location_name,
        address_line_1,
        city,
        state,
        postal_code,
        country,
        status
    FROM silver.locations
    ON CONFLICT (location_id) DO NOTHING
    """

    with db.engine.begin() as conn:
        result = conn.execute(text(sql))
        print(f"  ✅ Loaded {result.rowcount if hasattr(result, 'rowcount') else '?'} locations")

    # 4. Populate gold.dim_date (populate separately)
    print("📋 Note: gold.dim_date should be populated separately")
    print("  Run: python populate_dim_date.py")

    # 5. Populate gold.fact_sales
    print("📋 Populating gold.fact_sales...")

    sql = """
    INSERT INTO gold.fact_sales (
        date_key, customer_sk, product_sk, location_sk,
        order_id, transaction_timestamp,
        quantity, unit_price, total_amount,
        hour_of_day, day_of_week
    )
    SELECT
        TO_CHAR(t.transaction_date, 'YYYYMMDD')::INTEGER as date_key,
        c.customer_sk,
        p.product_sk,
        l.location_sk,
        t.order_id,
        t.transaction_date,
        t.quantity,
        t.unit_price,
        t.total_amount,
        t.transaction_hour,
        t.transaction_day_of_week
    FROM silver.transactions t
    JOIN gold.dim_customer c ON t.customer_id = c.customer_id AND c.is_current = TRUE
    JOIN gold.dim_product p ON t.product_id = (
        SELECT product_id FROM silver.products WHERE product_sk = p.product_sk LIMIT 1
    )
    JOIN gold.dim_location l ON t.location_id = l.location_id
    ON CONFLICT DO NOTHING
    """

    try:
        with db.engine.begin() as conn:
            result = conn.execute(text(sql))
            print(f"  ✅ Loaded {result.rowcount if hasattr(result, 'rowcount') else '?'} sales facts")
    except Exception as e:
        print(f"  ⚠️  Fact table population may need adjustment: {str(e)}")
        print("  Note: Run populate_dim_date.py first to create date keys")

    print()

    # 6. Build customer metrics
    print("📋 Building gold.customer_metrics...")

    sql = """
    INSERT INTO gold.customer_metrics (
        customer_sk, recency_days, frequency, monetary_total,
        avg_order_value, total_orders, total_items,
        first_purchase_date, last_purchase_date, days_as_customer
    )
    SELECT
        c.customer_sk,
        EXTRACT(DAY FROM (NOW() - MAX(t.transaction_date))) as recency_days,
        COUNT(DISTINCT t.order_id) as frequency,
        SUM(t.total_amount) as monetary_total,
        AVG(t.total_amount) as avg_order_value,
        COUNT(DISTINCT t.order_id) as total_orders,
        SUM(t.quantity) as total_items,
        DATE(MIN(t.transaction_date)) as first_purchase_date,
        DATE(MAX(t.transaction_date)) as last_purchase_date,
        EXTRACT(DAY FROM (MAX(t.transaction_date) - MIN(t.transaction_date))) as days_as_customer
    FROM silver.transactions t
    JOIN gold.dim_customer c ON t.customer_id = c.customer_id AND c.is_current = TRUE
    GROUP BY c.customer_sk
    ON CONFLICT (customer_sk) DO UPDATE SET
        recency_days = EXCLUDED.recency_days,
        frequency = EXCLUDED.frequency,
        monetary_total = EXCLUDED.monetary_total,
        avg_order_value = EXCLUDED.avg_order_value,
        total_orders = EXCLUDED.total_orders,
        total_items = EXCLUDED.total_items,
        last_purchase_date = EXCLUDED.last_purchase_date,
        days_as_customer = EXCLUDED.days_as_customer,
        calculated_at = NOW()
    """

    with db.engine.begin() as conn:
        result = conn.execute(text(sql))
        print(f"  ✅ Calculated metrics for {result.rowcount if hasattr(result, 'rowcount') else '?'} customers")

    print()


def main():
    """Run complete transformation pipeline."""

    print("=" * 70)
    print("⚡ DATA TRANSFORMATION PIPELINE")
    print("=" * 70)
    print()

    db = RDSConnector()

    try:
        # Transform bronze → silver
        transform_bronze_to_silver(db)

        # Transform silver → gold
        transform_silver_to_gold(db)

        print("=" * 70)
        print("✅ TRANSFORMATION COMPLETE!")
        print("=" * 70)
        print()
        print("📊 Data Quality Layers:")
        print("   🥉 Bronze: Raw source data")
        print("   🥈 Silver: Cleaned, validated dimensions")
        print("   🥇 Gold: Analytics-ready star schema")
        print()
        print("💡 Next steps:")
        print("   1. Populate date dimension: python populate_dim_date.py")
        print("   2. Run ML models: python examples/analyze_from_rds.py")
        print("   3. View dashboard with gold data")

    except Exception as e:
        print(f"❌ Transformation failed: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    main()
