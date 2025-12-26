"""
Verify that data was loaded correctly from Square to Bronze → Silver → Gold.
Checks row counts, data quality, and timezone handling.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.utils.database import RDSConnector
from sqlalchemy import text
import pandas as pd


def print_header(title):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_bronze_layer(db):
    """Verify bronze layer data."""
    print_header("🥉 BRONZE LAYER VERIFICATION")

    # Get row count
    query = "SELECT COUNT(*) as count FROM bronze.sales_transactions"
    result = db.query_to_dataframe(query)
    total_rows = result['count'][0]
    print(f"Total rows in bronze.sales_transactions: {total_rows:,}")

    if total_rows == 0:
        print("❌ ERROR: No data in bronze layer!")
        return False

    # Get date range
    query = """
    SELECT
        MIN(date) as earliest_date,
        MAX(date) as latest_date,
        COUNT(DISTINCT DATE(date)) as unique_dates
    FROM bronze.sales_transactions
    """
    result = db.query_to_dataframe(query)
    print(f"Date range: {result['earliest_date'][0]} to {result['latest_date'][0]}")
    print(f"Unique dates: {result['unique_dates'][0]}")

    # Check timezone - look at sample timestamps
    query = """
    SELECT date,
           EXTRACT(TIMEZONE_HOUR FROM date) as tz_hour,
           EXTRACT(HOUR FROM date) as hour_of_day
    FROM bronze.sales_transactions
    ORDER BY date DESC
    LIMIT 5
    """
    result = db.query_to_dataframe(query)
    print("\nSample timestamps (most recent 5):")
    print(result.to_string(index=False))

    # Check for null values
    query = """
    SELECT
        COUNT(*) FILTER (WHERE order_id IS NULL) as null_order_ids,
        COUNT(*) FILTER (WHERE date IS NULL) as null_dates,
        COUNT(*) FILTER (WHERE product IS NULL) as null_products,
        COUNT(*) FILTER (WHERE amount IS NULL) as null_amounts,
        COUNT(*) FILTER (WHERE price IS NULL) as null_prices
    FROM bronze.sales_transactions
    """
    result = db.query_to_dataframe(query)
    print("\nNull value check:")
    for col in result.columns:
        null_count = result[col][0]
        if null_count > 0:
            print(f"  ⚠️  {col}: {null_count} null values")
        else:
            print(f"  ✅ {col}: 0 null values")

    # Product summary
    query = """
    SELECT
        COUNT(DISTINCT product) as unique_products,
        COUNT(DISTINCT base_product) as unique_base_products,
        COUNT(DISTINCT category) as unique_categories
    FROM bronze.sales_transactions
    """
    result = db.query_to_dataframe(query)
    print(f"\nProduct summary:")
    print(f"  Unique products: {result['unique_products'][0]}")
    print(f"  Unique base products: {result['unique_base_products'][0]}")
    print(f"  Unique categories: {result['unique_categories'][0]}")

    print("\n✅ Bronze layer verification complete")
    return True


def check_silver_layer(db):
    """Verify silver layer data."""
    print_header("🥈 SILVER LAYER VERIFICATION")

    # Check all silver tables
    tables = ['locations', 'customers', 'products', 'transactions']

    for table in tables:
        query = f"SELECT COUNT(*) as count FROM silver.{table}"
        result = db.query_to_dataframe(query)
        count = result['count'][0]
        print(f"silver.{table}: {count:,} rows")

        if count == 0:
            print(f"  ⚠️  WARNING: No data in silver.{table}")

    # Check transactions detail
    query = """
    SELECT
        MIN(transaction_date) as earliest,
        MAX(transaction_date) as latest,
        COUNT(DISTINCT order_id) as unique_orders,
        SUM(quantity) as total_items,
        SUM(total_amount) as total_revenue
    FROM silver.transactions
    """
    result = db.query_to_dataframe(query)
    print(f"\nTransaction details:")
    print(f"  Date range: {result['earliest'][0]} to {result['latest'][0]}")
    print(f"  Unique orders: {result['unique_orders'][0]:,}")
    print(f"  Total items: {result['total_items'][0]:,}")
    print(f"  Total revenue: ${result['total_revenue'][0]:,.2f}")

    print("\n✅ Silver layer verification complete")
    return True


def check_gold_layer(db):
    """Verify gold layer data."""
    print_header("🥇 GOLD LAYER VERIFICATION")

    # Check dimension tables
    dim_tables = ['dim_customer', 'dim_product', 'dim_location']

    for table in dim_tables:
        query = f"SELECT COUNT(*) as count FROM gold.{table}"
        result = db.query_to_dataframe(query)
        count = result['count'][0]
        print(f"gold.{table}: {count:,} rows")

        if count == 0:
            print(f"  ⚠️  WARNING: No data in gold.{table}")

    # Check fact_sales
    query = "SELECT COUNT(*) as count FROM gold.fact_sales"
    result = db.query_to_dataframe(query)
    fact_count = result['count'][0]
    print(f"gold.fact_sales: {fact_count:,} rows")

    if fact_count > 0:
        # Get fact details
        query = """
        SELECT
            MIN(transaction_timestamp) as earliest,
            MAX(transaction_timestamp) as latest,
            COUNT(DISTINCT order_id) as unique_orders,
            SUM(quantity) as total_items,
            SUM(total_amount) as total_revenue
        FROM gold.fact_sales
        """
        result = db.query_to_dataframe(query)
        print(f"\nFact sales details:")
        print(f"  Date range: {result['earliest'][0]} to {result['latest'][0]}")
        print(f"  Unique orders: {result['unique_orders'][0]:,}")
        print(f"  Total items: {result['total_items'][0]:,}")
        print(f"  Total revenue: ${result['total_revenue'][0]:,.2f}")

    # Check customer_metrics
    query = "SELECT COUNT(*) as count FROM gold.customer_metrics"
    result = db.query_to_dataframe(query)
    metrics_count = result['count'][0]
    print(f"\ngold.customer_metrics: {metrics_count:,} rows")

    if metrics_count > 0:
        # Sample metrics
        query = """
        SELECT
            AVG(frequency) as avg_frequency,
            AVG(monetary_total) as avg_monetary,
            AVG(recency_days) as avg_recency,
            MAX(total_orders) as max_orders
        FROM gold.customer_metrics
        """
        result = db.query_to_dataframe(query)
        print(f"\nCustomer metrics summary:")
        print(f"  Avg frequency: {result['avg_frequency'][0]:.2f} orders")
        print(f"  Avg monetary: ${result['avg_monetary'][0]:,.2f}")
        print(f"  Avg recency: {result['avg_recency'][0]:.1f} days")
        print(f"  Max orders: {result['max_orders'][0]}")

    print("\n✅ Gold layer verification complete")
    return True


def check_timezone_handling(db):
    """Verify timezone handling (PST)."""
    print_header("🕐 TIMEZONE VERIFICATION")

    # Check sample timestamps across layers
    print("Comparing timestamps across layers:")

    # Get a sample order_id from bronze
    query = "SELECT order_id FROM bronze.sales_transactions LIMIT 1"
    result = db.query_to_dataframe(query)
    if result.empty:
        print("No data to check")
        return False

    sample_order = result['order_id'][0]

    # Get timestamp from bronze
    query = f"""
    SELECT date,
           EXTRACT(HOUR FROM date) as hour,
           EXTRACT(TIMEZONE_HOUR FROM date) as tz_offset
    FROM bronze.sales_transactions
    WHERE order_id = '{sample_order}'
    LIMIT 1
    """
    bronze_result = db.query_to_dataframe(query)

    if not bronze_result.empty:
        print(f"\nSample order: {sample_order}")
        print(f"Bronze timestamp: {bronze_result['date'][0]}")
        print(f"Hour: {bronze_result['hour'][0]}")
        if 'tz_offset' in bronze_result.columns and pd.notna(bronze_result['tz_offset'][0]):
            tz_offset = bronze_result['tz_offset'][0]
            print(f"Timezone offset: {tz_offset} hours from UTC")
            if tz_offset == -8:
                print("✅ Timezone appears to be PST (UTC-8)")
            elif tz_offset == -7:
                print("✅ Timezone appears to be PDT (UTC-7)")
            else:
                print(f"⚠️  Unexpected timezone offset: {tz_offset}")
        else:
            print("⚠️  No timezone information in timestamp (stored as naive datetime)")

    # Check if timestamps look reasonable (business hours)
    query = """
    SELECT
        EXTRACT(HOUR FROM date) as hour,
        COUNT(*) as transaction_count
    FROM bronze.sales_transactions
    GROUP BY EXTRACT(HOUR FROM date)
    ORDER BY transaction_count DESC
    LIMIT 5
    """
    result = db.query_to_dataframe(query)
    print("\nTop 5 busiest hours of day:")
    for _, row in result.iterrows():
        hour = int(row['hour'])
        count = row['transaction_count']
        print(f"  Hour {hour:02d}:00 - {count:,} transactions")

    print("\n✅ Timezone verification complete")
    return True


def check_data_consistency(db):
    """Check data consistency across layers."""
    print_header("🔍 DATA CONSISTENCY CHECK")

    # Compare row counts between bronze and silver
    bronze_query = "SELECT COUNT(*) as count FROM bronze.sales_transactions"
    bronze_result = db.query_to_dataframe(bronze_query)
    bronze_count = bronze_result['count'][0]

    silver_query = "SELECT COUNT(*) as count FROM silver.transactions"
    silver_result = db.query_to_dataframe(silver_query)
    silver_count = silver_result['count'][0]

    print(f"Bronze transactions: {bronze_count:,}")
    print(f"Silver transactions: {silver_count:,}")

    if bronze_count == silver_count:
        print("✅ Row counts match between bronze and silver")
    else:
        diff = bronze_count - silver_count
        pct_diff = (diff / bronze_count * 100) if bronze_count > 0 else 0
        print(f"⚠️  Difference: {diff:,} rows ({pct_diff:.2f}%)")
        print("   (Some filtering may be expected during transformation)")

    # Compare silver and gold
    gold_query = "SELECT COUNT(*) as count FROM gold.fact_sales"
    gold_result = db.query_to_dataframe(gold_query)
    gold_count = gold_result['count'][0]

    print(f"Gold fact_sales: {gold_count:,}")

    if silver_count == gold_count:
        print("✅ Row counts match between silver and gold")
    else:
        diff = silver_count - gold_count
        pct_diff = (diff / silver_count * 100) if silver_count > 0 else 0
        print(f"⚠️  Difference: {diff:,} rows ({pct_diff:.2f}%)")

    print("\n✅ Consistency check complete")
    return True


def main():
    """Run all verification checks."""
    print_header("⚡ DATA LOAD VERIFICATION")
    print(f"Verification started at: {datetime.now()}")

    db = RDSConnector()

    try:
        # Run all checks
        checks = [
            ("Bronze Layer", check_bronze_layer),
            ("Silver Layer", check_silver_layer),
            ("Gold Layer", check_gold_layer),
            ("Timezone Handling", check_timezone_handling),
            ("Data Consistency", check_data_consistency),
        ]

        results = []
        for name, check_func in checks:
            try:
                result = check_func(db)
                results.append((name, result))
            except Exception as e:
                print(f"\n❌ Error in {name}: {str(e)}")
                results.append((name, False))

        # Summary
        print_header("📊 VERIFICATION SUMMARY")
        all_passed = True
        for name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {name}")
            if not result:
                all_passed = False

        print("\n" + "=" * 70)
        if all_passed:
            print("🎉 All verification checks passed!")
        else:
            print("⚠️  Some verification checks failed - review output above")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    main()
