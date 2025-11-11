#!/usr/bin/env python3
"""
Fix timezone issue in fact_sales order_hour column.

The order_hour was being extracted from UTC timestamps instead of local time,
causing hourly charts to show activity during closed hours.

This script:
1. Adds timezone column to dim_location (if not exists)
2. Sets default timezone (you can change this to your actual timezone)
3. Recalculates order_hour for all existing fact_sales records using local time
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def fix_timezone():
    """Fix timezone handling in fact_sales."""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found in .env file")
        return

    print("🔧 Fixing timezone in fact_sales...")
    print("=" * 60)

    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    try:
        # Step 1: Add timezone column to dim_location if it doesn't exist
        print("\n📍 Step 1: Adding timezone column to dim_location...")
        cursor.execute("""
            ALTER TABLE gold.dim_location
            ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'America/Los_Angeles';
        """)
        print("  ✅ Timezone column added")

        # Step 2: Let user know to verify their timezone
        print("\n⚠️  IMPORTANT: Verify your store timezone!")
        print("  Default set to: America/Los_Angeles (Pacific Time)")
        print("  Common US timezones:")
        print("    - America/Los_Angeles (Pacific)")
        print("    - America/Denver (Mountain)")
        print("    - America/Chicago (Central)")
        print("    - America/New_York (Eastern)")
        print("\n  To update, run:")
        print("    UPDATE gold.dim_location SET timezone = 'YOUR_TIMEZONE';")

        # Step 3: Update order_hour in fact_sales to use local timezone
        print("\n🔄 Step 2: Recalculating order_hour with correct timezone...")
        print("  (This may take a few minutes for large datasets...)")

        cursor.execute("""
            UPDATE gold.fact_sales fs
            SET order_hour = EXTRACT(HOUR FROM (fs.order_timestamp AT TIME ZONE 'UTC' AT TIME ZONE dl.timezone))::INTEGER,
                order_day_of_week = EXTRACT(DOW FROM (fs.order_timestamp AT TIME ZONE 'UTC' AT TIME ZONE dl.timezone))::INTEGER
            FROM gold.dim_location dl
            WHERE fs.location_sk = dl.location_sk;
        """)

        rows_updated = cursor.rowcount
        print(f"  ✅ Updated {rows_updated:,} rows")

        # Commit changes
        conn.commit()
        print("\n✅ Timezone fix completed successfully!")

        # Show sample of corrected data
        print("\n📊 Sample of corrected hours:")
        cursor.execute("""
            SELECT
                order_timestamp AT TIME ZONE 'UTC' as utc_time,
                order_timestamp AT TIME ZONE 'UTC' AT TIME ZONE dl.timezone as local_time,
                order_hour as hour,
                COUNT(*) as orders
            FROM gold.fact_sales fs
            JOIN gold.dim_location dl ON fs.location_sk = dl.location_sk
            GROUP BY 1, 2, 3
            ORDER BY utc_time DESC
            LIMIT 5;
        """)

        print("\nUTC Time            | Local Time          | Hour | Orders")
        print("-" * 70)
        for row in cursor.fetchall():
            print(f"{row[0]} | {row[1]} | {row[2]:4d} | {row[3]:6d}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    print("\n" + "=" * 60)
    print("Done! Refresh your dashboard to see corrected hourly charts.")

if __name__ == '__main__':
    fix_timezone()
