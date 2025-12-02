"""
Populate gold.dim_date dimension table.
Creates date records for analytics and time-based analysis.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.database import RDSConnector
from sqlalchemy import text
import pandas as pd


def populate_dim_date(start_year=2022, end_year=2030):
    """
    Populate date dimension with all dates in range.

    Args:
        start_year: Starting year (default 2022 - first sales date 07/01/2022)
        end_year: Ending year
    """

    print("=" * 70)
    print("📅 POPULATING DATE DIMENSION")
    print("=" * 70)
    print(f"Date range: {start_year}-01-01 to {end_year}-12-31")
    print()

    db = RDSConnector()

    # Generate date range
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)

    dates = pd.date_range(start=start_date, end=end_date, freq='D')

    print(f"Generating {len(dates):,} date records...")

    # Prepare date data
    date_data = []
    for date in dates:
        date_key = int(date.strftime('%Y%m%d'))

        date_data.append({
            'date_key': date_key,
            'full_date': date.date(),
            'year': date.year,
            'quarter': (date.month - 1) // 3 + 1,
            'month': date.month,
            'month_name': date.strftime('%B'),
            'week': date.isocalendar()[1],
            'day_of_month': date.day,
            'day_of_week': date.weekday(),  # 0 = Monday
            'day_name': date.strftime('%A'),
            'is_weekend': date.weekday() >= 5
        })

    # Insert using parameterized queries to avoid SQL statement size limits
    batch_size = 500  # Can use larger batches with parameterized queries
    total_inserted = 0

    sql = """
    INSERT INTO gold.dim_date (
        date_key, full_date, year, quarter, month, month_name,
        week, day_of_month, day_of_week, day_name, is_weekend
    )
    VALUES (:date_key, :full_date, :year, :quarter, :month, :month_name,
            :week, :day_of_month, :day_of_week, :day_name, :is_weekend)
    ON CONFLICT (date_key) DO NOTHING
    """

    for i in range(0, len(date_data), batch_size):
        batch = date_data[i:i+batch_size]

        with db.engine.begin() as conn:
            conn.execute(text(sql), batch)

        total_inserted += len(batch)
        print(f"  Progress: {total_inserted:,} / {len(date_data):,} dates")

    print()
    print(f"✅ Populated {total_inserted:,} dates")

    # Verify
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM gold.dim_date"))
        count = result.fetchone()[0]

    print(f"📊 Total dates in dimension: {count:,}")

    print()
    print("=" * 70)
    print("✅ DATE DIMENSION COMPLETE!")
    print("=" * 70)

    db.close()


if __name__ == "__main__":
    populate_dim_date()
