"""
Quick script to sync Square data for a custom date range.
Use this to get all historical data from a specific start date.
"""

import sys
from src.integrations.square_connector import SquareDataConnector
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def sync_custom_range(start_date, end_date):
    """
    Sync Square data for a custom date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    print("=" * 70)
    print("📦 SQUARE HISTORICAL DATA SYNC")
    print("=" * 70)
    print(f"Date Range: {start_date} to {end_date}")
    print()

    try:
        connector = SquareDataConnector()

        # Test connection first
        result = connector.test_connection()
        if not result['success']:
            print(f"❌ {result['message']}")
            return

        print(f"✅ Connected to Square")
        print(f"   Locations: {result['locations']}")
        print()

        # Fetch data
        print(f"📡 Fetching data from {start_date} to {end_date}...")
        orders_df = connector.sync_to_csv(
            start_date=start_date,
            end_date=end_date,
            output_path='data/raw/square_sales.csv'
        )

        if orders_df is not None and not orders_df.empty:
            print()
            print("=" * 70)
            print("✅ SYNC COMPLETE!")
            print("=" * 70)
            print(f"Total Transactions: {len(orders_df):,}")
            print(f"Unique Customers: {orders_df['customer_id'].nunique():,}")
            print(f"Unique Products: {orders_df['product'].nunique():,}")
            print(f"Total Revenue: ${orders_df['price'].sum():,.2f}")
            print(f"Date Range: {orders_df['date'].min()} to {orders_df['date'].max()}")
            print()
            print(f"💾 Data saved to: data/raw/square_sales.csv")
        else:
            print("⚠️  No data found for this date range")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python sync_custom_range.py START_DATE END_DATE")
        print()
        print("Examples:")
        print("  # Get all data from 2020 onwards")
        print("  python sync_custom_range.py 2020-01-01 2024-12-31")
        print()
        print("  # Get specific year")
        print("  python sync_custom_range.py 2023-01-01 2023-12-31")
        print()
        print("  # Get everything from when you started using Square")
        print("  python sync_custom_range.py 2018-01-01 2024-12-31")
        sys.exit(1)

    start_date = sys.argv[1]
    end_date = sys.argv[2]

    # Validate date format
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    sync_custom_range(start_date, end_date)
