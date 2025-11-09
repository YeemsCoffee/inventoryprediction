"""
Automated Square data sync for production use.
Syncs data from Square POS daily and updates the dashboard data.
"""

from src.integrations.square_connector import SquareDataConnector
from datetime import datetime, timedelta
import schedule
import time
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    filename='sync.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def sync_yesterday():
    """Sync yesterday's data from Square."""
    try:
        # Get environment setting from .env
        environment = os.getenv('SQUARE_ENVIRONMENT', 'production')
        connector = SquareDataConnector(environment=environment)

        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')

        logging.info(f"Starting Square sync for {yesterday}")
        print(f"📡 Syncing Square data for {yesterday} (using {environment} environment)...")

        connector.sync_to_csv(
            start_date=yesterday,
            end_date=today,
            output_path='data/raw/square_sales.csv'
        )

        logging.info("Square sync completed successfully")
        print("✅ Sync complete!")

    except Exception as e:
        logging.error(f"Sync failed: {str(e)}")
        print(f"❌ Sync failed: {str(e)}")

def backfill_data(days=90):
    """Initial backfill of historical data."""
    try:
        # Get environment setting from .env
        environment = os.getenv('SQUARE_ENVIRONMENT', 'production')
        connector = SquareDataConnector(environment=environment)

        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end = datetime.now().strftime('%Y-%m-%d')

        logging.info(f"Starting backfill: {start} to {end}")
        print(f"📦 Backfilling {days} days of data (using {environment} environment)...")

        connector.sync_to_csv(
            start_date=start,
            end_date=end,
            output_path='data/raw/square_sales.csv'
        )

        logging.info("Backfill completed successfully")
        print("✅ Backfill complete!")

    except Exception as e:
        logging.error(f"Backfill failed: {str(e)}")
        print(f"❌ Backfill failed: {str(e)}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'backfill':
        # Run backfill
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
        backfill_data(days)

    elif len(sys.argv) > 1 and sys.argv[1] == 'once':
        # Run sync once
        sync_yesterday()

    else:
        # Run scheduled sync
        print("🚀 Starting automated Square sync scheduler...")
        print("📅 Will sync daily at 1:00 AM")
        print("⏹️  Press Ctrl+C to stop")
        print()

        # Schedule daily sync at 1 AM
        schedule.every().day.at("01:00").do(sync_yesterday)

        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)
