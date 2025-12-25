#!/usr/bin/env python3
"""
Review TFT demand forecasts and display key insights.
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.database import RDSConnector

def review_predictions():
    """Review and display predictions from the database."""

    db = RDSConnector()

    print("=" * 80)
    print("📊 DEMAND FORECAST REVIEW")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. Summary by product and location
    print("=" * 80)
    print("1. SUMMARY BY PRODUCT & LOCATION (30-Day Totals)")
    print("=" * 80)

    query1 = """
    SELECT
        product_name,
        location,
        COUNT(*) as forecast_days,
        MIN(forecast_date) as first_forecast,
        MAX(forecast_date) as last_forecast,
        ROUND(AVG(forecasted_quantity), 2) as avg_daily_qty,
        ROUND(SUM(forecasted_quantity), 2) as total_30day_qty
    FROM predictions.demand_forecasts
    GROUP BY product_name, location
    ORDER BY location, total_30day_qty DESC
    """

    with db.engine.connect() as conn:
        df1 = pd.read_sql(query1, conn)

    for location in df1['location'].unique():
        print(f"\n📍 {location}")
        print("-" * 80)
        location_df = df1[df1['location'] == location]
        for _, row in location_df.iterrows():
            print(f"  {row['product_name'][:45]:45s} | "
                  f"Avg: {row['avg_daily_qty']:6.1f}/day | "
                  f"30-Day Total: {row['total_30day_qty']:8.1f}")

    print("\n")

    # 2. Next 7 days detail for top product at each location
    print("=" * 80)
    print("2. NEXT 7 DAYS FORECAST (Top Product per Location)")
    print("=" * 80)

    query2 = """
    WITH top_products AS (
        SELECT DISTINCT ON (location)
            product_name,
            location
        FROM predictions.demand_forecasts
        GROUP BY product_name, location
        ORDER BY location, SUM(forecasted_quantity) DESC
    )
    SELECT
        p.product_name,
        p.location,
        p.forecast_date,
        TO_CHAR(p.forecast_date, 'Dy') as day_of_week,
        ROUND(p.forecasted_quantity, 1) as quantity
    FROM predictions.demand_forecasts p
    INNER JOIN top_products tp
        ON p.product_name = tp.product_name
        AND p.location = tp.location
    WHERE p.forecast_date <= CURRENT_DATE + 6
    ORDER BY p.location, p.forecast_date
    """

    with db.engine.connect() as conn:
        df2 = pd.read_sql(query2, conn)

    for location in df2['location'].unique():
        location_df = df2[df2['location'] == location]
        product = location_df['product_name'].iloc[0]
        print(f"\n📍 {location} - {product}")
        print("-" * 80)
        print(f"{'Date':<12} {'Day':<5} {'Quantity':>10}")
        print("-" * 80)
        for _, row in location_df.iterrows():
            print(f"{row['forecast_date']!s:<12} {row['day_of_week']:<5} {row['quantity']:>10.1f}")

    print("\n")

    # 3. Week 1 material planning summary
    print("=" * 80)
    print("3. WEEK 1 MATERIAL PLANNING (Next 7 Days)")
    print("=" * 80)

    query3 = """
    SELECT
        location,
        product_name,
        ROUND(SUM(forecasted_quantity), 1) as week1_total,
        ROUND(AVG(forecasted_quantity), 1) as daily_avg
    FROM predictions.demand_forecasts
    WHERE forecast_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 6
    GROUP BY location, product_name
    ORDER BY location, week1_total DESC
    """

    with db.engine.connect() as conn:
        df3 = pd.read_sql(query3, conn)

    for location in df3['location'].unique():
        print(f"\n📍 {location}")
        print("-" * 80)
        location_df = df3[df3['location'] == location]
        print(f"{'Product':<45} {'7-Day Total':>12} {'Daily Avg':>10}")
        print("-" * 80)
        for _, row in location_df.iterrows():
            print(f"{row['product_name'][:45]:<45} {row['week1_total']:>12.1f} {row['daily_avg']:>10.1f}")

        total = location_df['week1_total'].sum()
        print("-" * 80)
        print(f"{'TOTAL':<45} {total:>12.1f}")

    print("\n")

    # 4. Day-of-week patterns
    print("=" * 80)
    print("4. DAY-OF-WEEK PATTERNS (Average across all products)")
    print("=" * 80)

    query4 = """
    SELECT
        TO_CHAR(forecast_date, 'Day') as day_of_week,
        EXTRACT(DOW FROM forecast_date) as dow_num,
        location,
        ROUND(AVG(forecasted_quantity), 1) as avg_quantity
    FROM predictions.demand_forecasts
    GROUP BY TO_CHAR(forecast_date, 'Day'), EXTRACT(DOW FROM forecast_date), location
    ORDER BY location, dow_num
    """

    with db.engine.connect() as conn:
        df4 = pd.read_sql(query4, conn)

    for location in df4['location'].unique():
        print(f"\n📍 {location}")
        print("-" * 80)
        location_df = df4[df4['location'] == location]
        for _, row in location_df.iterrows():
            print(f"  {row['day_of_week']:<10} {row['avg_quantity']:>8.1f}")

    print("\n")
    print("=" * 80)
    print("✅ Review Complete")
    print("=" * 80)
    print()

if __name__ == '__main__':
    review_predictions()
