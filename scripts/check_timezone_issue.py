#!/usr/bin/env python3
"""
Quick diagnostic to check timezone issue in hourly data.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("ERROR: DATABASE_URL not found")
    exit(1)

conn = psycopg2.connect(database_url)
cursor = conn.cursor()

print("🔍 Checking timezone configuration and hourly data...")
print("=" * 80)

# Check if timezone column exists
print("\n1. Checking if timezone column exists in dim_location:")
cursor.execute("""
    SELECT column_name, data_type, column_default
    FROM information_schema.columns
    WHERE table_schema = 'gold'
    AND table_name = 'dim_location'
    AND column_name = 'timezone';
""")

result = cursor.fetchone()
if result:
    print(f"  ✅ Timezone column exists: {result[0]} ({result[1]}), default: {result[2]}")
else:
    print("  ❌ Timezone column DOES NOT exist - you need to run fix_timezone_in_fact_sales.py")

# Check current timezone setting
print("\n2. Current timezone setting for locations:")
cursor.execute("SELECT location_name, timezone FROM gold.dim_location;")
for row in cursor.fetchall():
    print(f"  📍 {row[0]}: {row[1] if row[1] else 'NOT SET'}")

# Show sample of actual order times
print("\n3. Sample of order timestamps and extracted hours:")
cursor.execute("""
    SELECT
        order_timestamp,
        order_timestamp AT TIME ZONE 'UTC' as utc_time,
        order_hour,
        COUNT(*) as num_orders
    FROM gold.fact_sales
    GROUP BY order_timestamp, order_hour
    ORDER BY order_timestamp DESC
    LIMIT 10;
""")

print("\n  Order Timestamp (DB) | UTC Time            | Extracted Hour | # Orders")
print("  " + "-" * 75)
for row in cursor.fetchall():
    print(f"  {row[0]} | {row[1]} | {row[2]:14d} | {row[3]:8d}")

# Show hourly distribution
print("\n4. Hourly distribution of orders:")
cursor.execute("""
    SELECT order_hour, COUNT(*) as num_orders
    FROM gold.fact_sales
    GROUP BY order_hour
    ORDER BY order_hour;
""")

print("\n  Hour | # Orders | Bar Chart")
print("  " + "-" * 50)
max_orders = max([row[1] for row in cursor.fetchall()] or [1])
cursor.execute("""
    SELECT order_hour, COUNT(*) as num_orders
    FROM gold.fact_sales
    GROUP BY order_hour
    ORDER BY order_hour;
""")
for row in cursor.fetchall():
    bar_length = int((row[1] / max_orders) * 30)
    bar = "█" * bar_length
    print(f"  {row[0]:4d} | {row[1]:8d} | {bar}")

print("\n" + "=" * 80)
print("\n💡 What to look for:")
print("  - Hours should match your actual business hours (e.g., 7-17 for 7 AM - 5 PM)")
print("  - If hours are off by 7-8, that's UTC vs Pacific time issue")
print("  - If timezone column doesn't exist, run: python scripts/fix_timezone_in_fact_sales.py")

cursor.close()
conn.close()
