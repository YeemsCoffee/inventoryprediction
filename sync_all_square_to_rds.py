"""
Pull ALL Square historical data to RDS and run ML analysis.
Complete pipeline using database as source of truth.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integrations.square_connector import SquareDataConnector
from src.utils.database import RDSConnector
from src.app import CustomerTrendApp


def sync_all_square_to_rds(start_date: str, end_date: str):
    """
    Pull all Square data to RDS and run ML analysis.

    Args:
        start_date: Start date (YYYY-MM-DD) - when you started using Square
        end_date: End date (YYYY-MM-DD) - usually today
    """

    print("=" * 70)
    print("📊 COMPLETE SQUARE → RDS → ML PIPELINE")
    print("=" * 70)

    # Step 1: Connect to RDS
    print("\n📋 Step 1: Connect to Amazon RDS")
    print("-" * 70)

    try:
        db = RDSConnector()
        conn_result = db.test_connection()

        if not conn_result['success']:
            print(f"❌ {conn_result['message']}")
            return

        print(f"✅ Connected to: {conn_result['database']}")
        print(f"   Host: {conn_result['host']}")
        print(f"   Tables: {conn_result['table_count']}")

    except ValueError as e:
        print(f"❌ {str(e)}")
        print("\n⚠️  Make sure your .env file has:")
        print("   DATABASE_URL=postgresql://user:password@your-rds-endpoint:5432/dbname")
        return

    # Step 2: Connect to Square
    print("\n📋 Step 2: Connect to Square API")
    print("-" * 70)

    try:
        square = SquareDataConnector(environment='production')
        square_result = square.test_connection()

        if not square_result['success']:
            print(f"❌ {square_result['message']}")
            db.close()
            return

        print(f"✅ {square_result['message']}")
        print(f"   Locations: {square_result['locations']}")

    except ValueError as e:
        print(f"❌ {str(e)}")
        print("\nMake sure your .env has: SQUARE_ACCESS_TOKEN=your_token")
        db.close()
        return

    # Step 3: Sync ALL Square data to RDS
    print("\n📋 Step 3: Sync ALL Square Data to RDS")
    print("-" * 70)
    print(f"📅 Date Range: {start_date} to {end_date}")
    print()

    try:
        # Get a preview of what we'll sync
        print("🔍 Previewing data...")
        preview_df = square.fetch_orders(start_date, end_date)

        if preview_df.empty:
            print("⚠️  No Square data found for this date range")
            db.close()
            return

        print(f"📊 Found {len(preview_df):,} transactions to sync")
        print(f"   Date Range: {preview_df['date'].min()} to {preview_df['date'].max()}")
        print(f"   Products: {preview_df['product'].nunique():,} unique items (with modifiers)")
        print(f"   Revenue: ${preview_df['price'].sum():,.2f}")
        print()

        # Sync to database
        print("💾 Syncing to RDS database...")
        rows_synced = db.sync_square_to_database(
            square_connector=square,
            start_date=start_date,
            end_date=end_date,
            table_name='sales_transactions'
        )

        print(f"✅ Synced {rows_synced:,} transactions to database")

    except Exception as e:
        print(f"❌ Sync failed: {str(e)}")
        db.close()
        return

    # Step 4: Get database statistics
    print("\n📋 Step 4: Database Statistics")
    print("-" * 70)

    stats = db.get_table_stats('sales_transactions')
    print(f"Total Records in RDS: {stats.get('total_rows', 0):,}")
    print(f"Unique Customers: {stats.get('unique_customers', 0):,}")
    print(f"Unique Products: {stats.get('unique_products', 0):,}")
    print(f"Date Range: {stats.get('earliest_date')} to {stats.get('latest_date')}")
    print(f"Total Revenue: ${stats.get('total_revenue', 0):,.2f}")
    print()

    # Step 5: Pull data from RDS for ML analysis
    print("\n📋 Step 5: Load Data from RDS for ML Analysis")
    print("-" * 70)

    print("📥 Pulling data from RDS...")
    df = db.get_sales_data()

    print(f"✅ Retrieved {len(df):,} transactions from database")
    print()

    # Step 6: Run ML Analysis on RDS data
    print("\n📋 Step 6: Run ML Analysis on Database Data")
    print("-" * 70)

    try:
        app = CustomerTrendApp()
        app.data = df

        # Ensure date column is datetime
        if 'date' in app.data.columns:
            app.data['date'] = pd.to_datetime(app.data['date'])

        print("✅ Data loaded into ML pipeline")
        print()

        # Generate comprehensive analysis
        print("🔮 Generating Full ML Report...")
        print("   This may take a moment...")
        print()

        report = app.generate_full_report(n_segments=4)

        # Display results
        print("\n" + "=" * 70)
        print("📊 ML ANALYSIS RESULTS")
        print("=" * 70)
        app.print_summary(report)
        print("=" * 70)

        # Show top products with modifiers
        if 'product' in df.columns:
            print("\n" + "=" * 70)
            print("🛍️  TOP 15 PRODUCTS (With Modifiers)")
            print("=" * 70)

            top_products = df.groupby('product').agg({
                'amount': 'sum',
                'price': 'sum'
            }).sort_values('amount', ascending=False).head(15)

            for idx, (product, row) in enumerate(top_products.iterrows(), 1):
                print(f"{idx:2d}. {product}")
                print(f"    Qty: {int(row['amount']):,} | Revenue: ${row['price']:,.2f}")

    except Exception as e:
        print(f"❌ ML Analysis error: {str(e)}")
        import traceback
        traceback.print_exc()

    # Step 7: Summary
    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 70)
    print("\n📊 Data Flow:")
    print("  Square API → Amazon RDS → ML Analysis → Business Insights")
    print()
    print("💡 Next Steps:")
    print("  • Your data is now in RDS database")
    print("  • Run analysis anytime: python examples/analyze_from_rds.py")
    print("  • View dashboard: python -m src.dashboard.app")
    print("  • Get inventory recommendations: python examples/inventory_recommendations.py")
    print()

    # Close database connection
    db.close()


if __name__ == "__main__":
    import argparse
    import pandas as pd

    parser = argparse.ArgumentParser(
        description='Pull all Square data to RDS and run ML analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Get all data from 2020 onwards
  python sync_all_square_to_rds.py --start 2020-01-01

  # Specific date range
  python sync_all_square_to_rds.py --start 2022-01-01 --end 2024-12-31

  # Get last N years
  python sync_all_square_to_rds.py --years 3

This will:
  1. Connect to your RDS database
  2. Pull ALL Square data (with modifiers!)
  3. Sync to database
  4. Run complete ML analysis on database data
  5. Show seasonal trends, customer segments, forecasts
        """
    )

    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    date_group.add_argument('--years', type=int, help='Number of years back from today')

    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD), defaults to today')

    args = parser.parse_args()

    # Calculate date range
    if args.years:
        end_date = args.end or datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.years*365)).strftime('%Y-%m-%d')
    else:
        start_date = args.start
        end_date = args.end or datetime.now().strftime('%Y-%m-%d')

    print()
    print(f"📅 Syncing Square data from {start_date} to {end_date}")
    print()

    # Run the full pipeline
    sync_all_square_to_rds(start_date, end_date)
