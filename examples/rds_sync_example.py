"""
Example: Sync Square data to Amazon RDS and run ML analysis.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integrations.square_connector import SquareDataConnector
from src.utils.database import RDSConnector
from src.app import CustomerTrendApp


def main():
    """Demonstrate Square to RDS sync and ML analysis."""

    print("=" * 70)
    print("SQUARE → AMAZON RDS → ML ANALYSIS PIPELINE")
    print("=" * 70)

    # Step 1: Test database connection
    print("\n📋 Step 1: Connect to Amazon RDS")
    print("-" * 70)

    try:
        db = RDSConnector()
        conn_result = db.test_connection()

        if conn_result['success']:
            print(f"✅ {conn_result['message']}")
            print(f"   Database: {conn_result['database']}")
            print(f"   Host: {conn_result['host']}")
            print(f"   Existing tables: {conn_result['table_count']}")
        else:
            print(f"❌ {conn_result['message']}")
            return

    except ValueError as e:
        print(f"⚠️  {str(e)}")
        print("\nSetup instructions:")
        print("1. Create an Amazon RDS database (PostgreSQL or MySQL)")
        print("2. Add DATABASE_URL to your .env file:")
        print("   DATABASE_URL=postgresql://user:password@your-rds-endpoint:5432/dbname")
        print("\nFor PostgreSQL RDS endpoint example:")
        print("   mydb.abc123.us-east-1.rds.amazonaws.com")
        return

    # Step 2: Connect to Square
    print("\n📋 Step 2: Connect to Square API")
    print("-" * 70)

    try:
        square = SquareDataConnector(environment='production')  # or 'sandbox'
        square_result = square.test_connection()

        if square_result['success']:
            print(f"✅ {square_result['message']}")
            print(f"   Locations: {square_result['locations']}")
        else:
            print(f"❌ {square_result['message']}")
            return

    except ValueError as e:
        print(f"⚠️  {str(e)}")
        print("\nTo setup Square API:")
        print("1. Get access token from https://developer.squareup.com")
        print("2. Add to .env file: SQUARE_ACCESS_TOKEN=your_token")
        return

    # Step 3: Sync data from Square to RDS
    print("\n📋 Step 3: Sync Square Data to RDS")
    print("-" * 70)

    # Set date range (last 90 days)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

    print(f"Syncing data from {start_date} to {end_date}...")

    try:
        rows_synced = db.sync_square_to_database(
            square_connector=square,
            start_date=start_date,
            end_date=end_date,
            table_name='sales_transactions'
        )

        print(f"✅ Synced {rows_synced} transactions to database")

    except Exception as e:
        print(f"❌ Sync failed: {str(e)}")
        return

    # Step 4: Get database stats
    print("\n📋 Step 4: Database Statistics")
    print("-" * 70)

    stats = db.get_table_stats('sales_transactions')
    print(f"Total Rows: {stats.get('total_rows', 0):,}")
    print(f"Unique Customers: {stats.get('unique_customers', 0):,}")
    print(f"Unique Products: {stats.get('unique_products', 0):,}")
    print(f"Date Range: {stats.get('earliest_date')} to {stats.get('latest_date')}")
    print(f"Total Revenue: ${stats.get('total_revenue', 0):,.2f}")

    # Step 5: Export to CSV for ML analysis
    print("\n📋 Step 5: Export Data for ML Analysis")
    print("-" * 70)

    df = db.export_to_csv(
        table_name='sales_transactions',
        output_path='data/raw/from_rds.csv',
        start_date=start_date,
        end_date=end_date
    )

    print(f"✅ Exported {len(df)} rows to data/raw/from_rds.csv")

    # Step 6: Run ML analysis
    print("\n📋 Step 6: Run ML Analysis on RDS Data")
    print("-" * 70)

    app = CustomerTrendApp()
    app.load_data_from_csv('data/raw/from_rds.csv')

    report = app.generate_full_report(n_segments=4)
    app.print_summary(report)

    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 70)
    print("\nYour data flow:")
    print("  Square POS → Amazon RDS → ML Analysis → Business Insights")
    print("\nNext steps:")
    print("  - Schedule this script to run daily for automatic syncing")
    print("  - View insights in the dashboard: python -m src.dashboard.app")
    print("  - Query your RDS database directly for custom analysis")

    # Close database connection
    db.close()


if __name__ == "__main__":
    main()
