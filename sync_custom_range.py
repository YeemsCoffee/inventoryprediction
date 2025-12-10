"""
Quick script to sync Square data for a custom date range.
Use this to get all historical data from a specific start date.
"""

import sys
import argparse
from src.integrations.square_connector import SquareDataConnector
from datetime import datetime, timedelta
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
    parser = argparse.ArgumentParser(
        description='Sync Square data for a custom date range',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get last 30 days of data
  python sync_custom_range.py --days 30

  # Get last 90 days
  python sync_custom_range.py --days 90

  # Get specific date range
  python sync_custom_range.py 2024-01-01 2024-12-31

  # Get all data from 2020 onwards
  python sync_custom_range.py 2020-01-01 2024-12-31
        """
    )

    parser.add_argument(
        '--days',
        type=int,
        help='Number of days of historical data to sync (e.g., --days 30 for last 30 days)'
    )
    parser.add_argument(
        'start_date',
        nargs='?',
        help='Start date in YYYY-MM-DD format'
    )
    parser.add_argument(
        'end_date',
        nargs='?',
        help='End date in YYYY-MM-DD format'
    )

    args = parser.parse_args()

    # Determine date range
    if args.days:
        # Use --days flag
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    elif args.start_date and args.end_date:
        # Use explicit date range
        start_date = args.start_date
        end_date = args.end_date

        # Validate date format
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    sync_custom_range(start_date, end_date)
