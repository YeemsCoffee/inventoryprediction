#!/usr/bin/env python3
"""
Check what predictions exist in the database and their dates.
"""
import os
from dotenv import load_dotenv
import psycopg2
from datetime import datetime

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=" * 80)
print("🔍 CHECKING PREDICTIONS IN DATABASE")
print("=" * 80)

# Check total predictions
cur.execute("SELECT COUNT(*) FROM predictions.demand_forecasts")
total = cur.fetchone()[0]
print(f"\n📊 Total predictions in database: {total}")

if total > 0:
    # Check date range
    cur.execute("""
        SELECT
            MIN(forecast_date) as earliest,
            MAX(forecast_date) as latest,
            COUNT(DISTINCT product_name) as products
        FROM predictions.demand_forecasts
    """)
    row = cur.fetchone()
    print(f"\n📅 Date range:")
    print(f"   Earliest forecast: {row[0]}")
    print(f"   Latest forecast: {row[1]}")
    print(f"   Unique products: {row[2]}")
    print(f"   Today's date: {datetime.now().date()}")

    # Check how many are in the future
    cur.execute("""
        SELECT COUNT(*)
        FROM predictions.demand_forecasts
        WHERE forecast_date >= CURRENT_DATE
    """)
    future_count = cur.fetchone()[0]
    print(f"\n🔮 Predictions dated today or future: {future_count}")

    if future_count == 0:
        print("\n⚠️  WARNING: No predictions dated for today or future!")
        print("   This is why dashboard shows no predictions.")
        print("   Solution: Re-run train_ml_models.py to generate fresh forecasts.")

    # Show sample predictions
    cur.execute("""
        SELECT
            forecast_date,
            product_name,
            forecasted_quantity,
            forecasted_revenue,
            model_type
        FROM predictions.demand_forecasts
        WHERE product_name NOT LIKE '%LSTM%'
        ORDER BY forecast_date DESC, forecasted_revenue DESC
        LIMIT 10
    """)

    print("\n📋 Sample predictions:")
    for row in cur.fetchall():
        print(f"   {row[0]} | {row[1][:30]:30s} | {row[2]:8.1f} units | ${row[3]:10,.2f} | {row[4]}")

    # Check what the dashboard query would return
    print("\n🖥️  Testing dashboard query (next 7 days)...")
    cur.execute("""
        SELECT
            product_name,
            COALESCE(AVG(forecasted_quantity), 0) as avg_quantity,
            COALESCE(AVG(forecasted_revenue), 0) as avg_revenue,
            model_type
        FROM predictions.demand_forecasts
        WHERE forecast_date >= CURRENT_DATE
        AND forecast_date <= CURRENT_DATE + INTERVAL '7 days'
        AND product_name NOT LIKE '%LSTM%'
        GROUP BY product_name, model_type
        ORDER BY avg_revenue DESC
        LIMIT 5
    """)

    dashboard_results = cur.fetchall()
    if dashboard_results:
        print(f"   ✅ Dashboard would show {len(dashboard_results)} products:")
        for row in dashboard_results:
            print(f"      {row[0][:35]:35s} | {row[1]:8.1f} units/day | ${row[2]:10,.2f}/day | {row[3]}")
    else:
        print("   ❌ Dashboard query returns 0 results!")
        print("   Reason: No predictions in date range (today to +7 days)")

else:
    print("\n❌ No predictions found in database!")
    print("   Run: python train_ml_models.py")

print("\n" + "=" * 80)

cur.close()
conn.close()
