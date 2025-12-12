#!/usr/bin/env python3
"""
Check if Gold layer has data.
"""

from src.utils.database import RDSConnector
from sqlalchemy import text

db = RDSConnector()

try:
    with db.engine.connect() as conn:
        # Check fact_sales
        result = conn.execute(text("SELECT COUNT(*) FROM gold.fact_sales"))
        fact_count = result.scalar()
        print(f"gold.fact_sales: {fact_count:,} rows")

        # Check dimension tables
        result = conn.execute(text("SELECT COUNT(*) FROM gold.dim_date"))
        dim_date_count = result.scalar()
        print(f"gold.dim_date: {dim_date_count:,} rows")

        result = conn.execute(text("SELECT COUNT(*) FROM gold.dim_product"))
        dim_product_count = result.scalar()
        print(f"gold.dim_product: {dim_product_count:,} rows")

        result = conn.execute(text("SELECT COUNT(*) FROM gold.dim_customer"))
        dim_customer_count = result.scalar()
        print(f"gold.dim_customer: {dim_customer_count:,} rows")

        # Check bronze/silver layers
        result = conn.execute(text("SELECT COUNT(*) FROM bronze.sales_transactions"))
        bronze_count = result.scalar()
        print(f"\nbronze.sales_transactions: {bronze_count:,} rows")

        if fact_count == 0 and bronze_count > 0:
            print("\n⚠️  Gold layer is empty but Bronze has data!")
            print("You need to run the transformation pipeline:")
            print("  python transform_bronze_to_gold.py")

except Exception as e:
    print(f"Error: {e}")

finally:
    db.close()
