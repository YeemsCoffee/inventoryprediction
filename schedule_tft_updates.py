"""
Schedule automated TFT forecast updates.
Runs forecasting pipeline daily or weekly to keep dashboard predictions fresh.
"""

import schedule
import time
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import run_tft_pipeline


def run_scheduled_forecast():
    """Run TFT forecast pipeline on schedule."""

    print()
    print("=" * 70)
    print(f"⏰ Scheduled Forecast Run - {datetime.now()}")
    print("=" * 70)

    try:
        run_tft_pipeline.run_tft_pipeline(
            forecast_days=30,
            max_epochs=20,  # Fewer epochs for faster updates
            batch_size=128,
            save_to_db=True
        )

        print()
        print(f"✅ Scheduled run completed at {datetime.now()}")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Scheduled run failed: {e}")
        print("=" * 70)


def start_scheduler(schedule_type: str = 'daily', time_str: str = '02:00'):
    """
    Start forecast scheduler.

    Args:
        schedule_type: 'daily' or 'weekly'
        time_str: Time to run (24-hour format, e.g., '02:00')
    """

    print("=" * 70)
    print("📅 TFT FORECAST SCHEDULER")
    print("=" * 70)
    print()
    print(f"Schedule: {schedule_type.capitalize()} at {time_str}")
    print()
    print("This will:")
    print(f"  • Run TFT forecasting pipeline {schedule_type}")
    print("  • Update predictions.demand_forecasts table")
    print("  • Keep dashboard forecasts fresh")
    print()
    print("⚠️  Keep this terminal window open for scheduler to run")
    print("   Press Ctrl+C to stop")
    print()
    print("=" * 70)

    # Setup schedule
    if schedule_type.lower() == 'daily':
        schedule.every().day.at(time_str).do(run_scheduled_forecast)
        print(f"✅ Scheduled: Daily at {time_str}")
    elif schedule_type.lower() == 'weekly':
        schedule.every().monday.at(time_str).do(run_scheduled_forecast)
        print(f"✅ Scheduled: Weekly (Mondays) at {time_str}")
    else:
        raise ValueError(f"Invalid schedule_type: {schedule_type}")

    print()
    print("⏳ Waiting for next scheduled run...")
    print("   (Or press Ctrl+C to exit)")
    print()

    # Run scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("⏹️  Scheduler stopped")
        print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Schedule TFT forecast updates')
    parser.add_argument('--schedule', type=str, default='daily',
                       choices=['daily', 'weekly'],
                       help='Update frequency (default: daily)')
    parser.add_argument('--time', type=str, default='02:00',
                       help='Time to run in 24-hour format (default: 02:00)')
    parser.add_argument('--run-now', action='store_true',
                       help='Run once immediately (no scheduling)')

    args = parser.parse_args()

    if args.run_now:
        print("🚀 Running TFT pipeline immediately...")
        run_scheduled_forecast()
    else:
        start_scheduler(args.schedule, args.time)
