#!/usr/bin/env python3
"""
Debug Gold layer data - check dates and joins.
"""

from src.utils.database import RDSConnector
from sqlalchemy import text

db = RDSConnector()

try:
    with db.engine.connect() as conn:
        # Check total rows in fact_sales
        result = conn.execute(text("SELECT COUNT(*) FROM gold.fact_sales"))
        print(f"Total rows in gold.fact_sales: {result.scalar():,}")

        # Check date range in fact_sales
        result = conn.execute(text("""
            SELECT
                MIN(d.date) as earliest,
                MAX(d.date) as latest,
                COUNT(*) as total
            FROM gold.fact_sales f
            JOIN gold.dim_date d ON f.date_key = d.date_key
        """))
        row = result.fetchone()
        print(f"\nDate range in fact_sales:")
        print(f"  Earliest: {row[0]}")
        print(f"  Latest: {row[1]}")
        print(f"  Total rows with date: {row[2]:,}")

        # Check for NULL foreign keys
        result = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE date_key IS NULL) as null_dates,
                COUNT(*) FILTER (WHERE product_sk IS NULL) as null_products,
                COUNT(*) FILTER (WHERE customer_sk IS NULL) as null_customers
            FROM gold.fact_sales
        """))
        row = result.fetchone()
        print(f"\nNULL foreign keys:")
        print(f"  NULL date_key: {row[0]:,}")
        print(f"  NULL product_sk: {row[1]:,}")
        print(f"  NULL customer_sk: {row[2]:,}")

        # Try query without date filter
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM gold.fact_sales f
            JOIN gold.dim_date d ON f.date_key = d.date_key
            JOIN gold.dim_product p ON f.product_sk = p.product_sk
        """))
        print(f"\nRows with successful joins (no date filter): {result.scalar():,}")

        # Try query with 1 year filter
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM gold.fact_sales f
            JOIN gold.dim_date d ON f.date_key = d.date_key
            JOIN gold.dim_product p ON f.product_sk = p.product_sk
            WHERE d.date >= CURRENT_DATE - INTERVAL '1 year'
        """))
        print(f"Rows with 1 year filter: {result.scalar():,}")

        print(f"\nCurrent date: {conn.execute(text('SELECT CURRENT_DATE')).scalar()}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
