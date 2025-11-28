"""
Sync Square data in chunks to avoid API timeouts.
Breaks large date ranges into smaller monthly/quarterly chunks.
"""

import sys
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integrations.square_connector import SquareDataConnector
from src.utils.database import RDSConnector


def sync_in_chunks(start_date: str, end_date: str, chunk_months: int = 3):
    """
    Sync Square data in chunks to avoid API timeouts.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        chunk_months: Size of each chunk in months (default: 3)
    """

    print("=" * 70)
    print("📊 CHUNKED SQUARE DATA SYNC")
    print("=" * 70)
    print(f"📅 Total Range: {start_date} to {end_date}")
    print(f"📦 Chunk Size: {chunk_months} months")
    print()

    # Connect to database
    try:
        db = RDSConnector()
        print(f"✅ Connected to RDS: {db.engine.url.database}")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return

    # Connect to Square
    try:
        square = SquareDataConnector(environment='production')
        result = square.test_connection()
        if not result['success']:
            print(f"❌ Square connection failed: {result['message']}")
            db.close()
            return
        print(f"✅ Connected to Square: {result['locations']}")
    except Exception as e:
        print(f"❌ Square connection failed: {str(e)}")
        db.close()
        return

    print()

    # Parse dates
    current_start = datetime.strptime(start_date, '%Y-%m-%d')
    final_end = datetime.strptime(end_date, '%Y-%m-%d')

    total_synced = 0
    chunk_num = 0
    failed_chunks = []

    print("=" * 70)
    print("🔄 STARTING CHUNKED SYNC")
    print("=" * 70)

    while current_start < final_end:
        chunk_num += 1

        # Calculate chunk end date
        chunk_end = current_start + relativedelta(months=chunk_months)
        if chunk_end > final_end:
            chunk_end = final_end

        chunk_start_str = current_start.strftime('%Y-%m-%d')
        chunk_end_str = chunk_end.strftime('%Y-%m-%d')

        print(f"\n📦 Chunk {chunk_num}: {chunk_start_str} to {chunk_end_str}")
        print("-" * 70)

        try:
            # Fetch this chunk
            print(f"📡 Fetching from Square...")
            orders_df = square.fetch_orders(chunk_start_str, chunk_end_str)

            if orders_df.empty:
                print(f"   ℹ️  No data for this period")
            else:
                print(f"   ✅ Found {len(orders_df):,} transactions")

                # Sync to database
                print(f"   💾 Syncing to RDS...")
                rows = db.insert_dataframe(
                    orders_df,
                    table_name='sales_transactions',
                    if_exists='append'
                )

                total_synced += len(orders_df)
                print(f"   ✅ Synced {len(orders_df):,} transactions")

            # Small delay to avoid rate limiting
            time.sleep(1)

        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            failed_chunks.append({
                'start': chunk_start_str,
                'end': chunk_end_str,
                'error': str(e)
            })

            # If it's a 502 error, wait longer before retrying
            if '502' in str(e):
                print(f"   ⏳ Waiting 10 seconds before next chunk (API overload)...")
                time.sleep(10)

        # Move to next chunk
        current_start = chunk_end

    # Summary
    print("\n" + "=" * 70)
    print("📊 SYNC SUMMARY")
    print("=" * 70)
    print(f"Total Chunks: {chunk_num}")
    print(f"Total Synced: {total_synced:,} transactions")
    print(f"Failed Chunks: {len(failed_chunks)}")

    if failed_chunks:
        print("\n⚠️  Failed Chunks (you can retry these):")
        for chunk in failed_chunks:
            print(f"   • {chunk['start']} to {chunk['end']}: {chunk['error']}")

    # Get final database stats
    print()
    stats = db.get_table_stats('sales_transactions')
    print(f"📊 Total in Database: {stats.get('total_rows', 0):,} transactions")
    print(f"   Revenue: ${stats.get('total_revenue', 0):,.2f}")
    print(f"   Date Range: {stats.get('earliest_date')} to {stats.get('latest_date')}")

    db.close()

    print("\n" + "=" * 70)
    print("✅ CHUNKED SYNC COMPLETE!")
    print("=" * 70)
    print("\n💡 Next: Run ML analysis on your database data:")
    print("   python examples/analyze_from_rds.py")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Sync Square data in chunks to avoid timeouts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Sync all data from 2020 in 3-month chunks
  python sync_square_chunked.py --start 2020-01-01 --chunk-months 3

  # Sync in smaller 1-month chunks (for very large datasets)
  python sync_square_chunked.py --start 2020-01-01 --chunk-months 1

  # Specific date range
  python sync_square_chunked.py --start 2022-01-01 --end 2024-12-31 --chunk-months 6

This breaks large date ranges into smaller chunks to avoid API timeouts.
        """
    )

    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--chunk-months', type=int, default=3,
                       help='Chunk size in months (default: 3)')

    args = parser.parse_args()

    end_date = args.end or datetime.now().strftime('%Y-%m-%d')

    sync_in_chunks(args.start, end_date, args.chunk_months)
