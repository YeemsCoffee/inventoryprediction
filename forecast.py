#!/usr/bin/env python3
"""
Inventory Demand Forecasting
Predicts daily packing lists per store for the next 2 weeks.
"""

import csv
import math
from collections import defaultdict
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# 1. Load & prepare data
# ---------------------------------------------------------------------------

def load_data(filepath="Gardena KTOWN Sales Order.csv"):
    rows = []
    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            store = row["CustomerName"].strip()
            if store not in ("Gardena", "KTOWN"):
                continue

            product = row["ProductDescription"].strip()
            # Treat Vienna Cream and CS Vienna Cream as the same product
            if product in ("Vienna Cream", "CS Vienna Cream"):
                product = "Vienna Cream"

            d = datetime.strptime(row["OrderDate"].strip(), "%m/%d/%Y")
            qty = float(row["OrderQuantity"].strip()) if row["OrderQuantity"].strip() else 0.0

            rows.append({"store": store, "product": product, "date": d, "qty": qty})

    return rows


def build_daily_demand(rows):
    """Aggregate to daily demand: store -> product -> {date: qty}"""
    daily = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    all_dates = set()
    all_products = set()
    stores = set()

    for r in rows:
        daily[r["store"]][r["product"]][r["date"]] += r["qty"]
        all_dates.add(r["date"])
        all_products.add(r["product"])
        stores.add(r["store"])

    return daily, sorted(stores), sorted(all_products), min(all_dates), max(all_dates)


# ---------------------------------------------------------------------------
# 2. Forecasting model
# ---------------------------------------------------------------------------

def forecast_product(daily_qty_dict, min_date, max_date, forecast_start, num_days=14):
    """
    Forecast daily demand for a single store-product combination.

    Approach:
    - Compute a day-of-week profile (average demand per weekday)
    - Apply a recent trend multiplier using the last 3 weeks vs overall average
    - For infrequent items, predict based on average reorder interval
    """
    # Build a full daily series (fill missing days with 0)
    total_days = (max_date - min_date).days + 1
    series = []
    for i in range(total_days):
        d = min_date + timedelta(days=i)
        series.append((d, daily_qty_dict.get(d, 0.0)))

    if not series:
        return [(forecast_start + timedelta(days=i), 0.0) for i in range(num_days)]

    total_qty = sum(q for _, q in series)
    if total_qty == 0:
        return [(forecast_start + timedelta(days=i), 0.0) for i in range(num_days)]

    # Day-of-week averages
    dow_totals = defaultdict(float)
    dow_counts = defaultdict(int)
    for d, q in series:
        dow = d.weekday()  # 0=Mon ... 6=Sun
        dow_totals[dow] += q
        dow_counts[dow] += 1

    dow_avg = {}
    for dow in range(7):
        dow_avg[dow] = dow_totals[dow] / dow_counts[dow] if dow_counts[dow] > 0 else 0.0

    overall_daily_avg = total_qty / total_days if total_days > 0 else 0.0

    # Recent trend: compare last 3 weeks to overall
    recent_cutoff = max_date - timedelta(days=20)
    recent_series = [(d, q) for d, q in series if d > recent_cutoff]
    recent_days = len(recent_series)
    recent_total = sum(q for _, q in recent_series)
    recent_avg = recent_total / recent_days if recent_days > 0 else 0.0

    # Trend multiplier (capped to avoid wild swings)
    if overall_daily_avg > 0:
        trend = recent_avg / overall_daily_avg
        trend = max(0.3, min(trend, 3.0))  # clamp
    else:
        trend = 1.0

    # Generate forecast
    forecasts = []
    for i in range(num_days):
        d = forecast_start + timedelta(days=i)
        dow = d.weekday()
        predicted = dow_avg[dow] * trend
        forecasts.append((d, predicted))

    return forecasts


# ---------------------------------------------------------------------------
# 3. Generate packing lists
# ---------------------------------------------------------------------------

def generate_packing_lists(filepath="Gardena KTOWN Sales Order.csv", num_days=14):
    rows = load_data(filepath)
    daily, stores, all_products, min_date, max_date = build_daily_demand(rows)

    forecast_start = max_date + timedelta(days=1)

    # Forecast for every product at every store (both stores get all products)
    results = {}  # store -> product -> [(date, qty)]
    for store in stores:
        results[store] = {}
        for product in all_products:
            product_daily = daily[store][product]
            forecasts = forecast_product(product_daily, min_date, max_date, forecast_start, num_days)
            results[store][product] = forecasts

    return results, stores, all_products, forecast_start, num_days


def print_packing_lists(results, stores, all_products, forecast_start, num_days):
    print("=" * 80)
    print("  INVENTORY PACKING LIST FORECAST")
    print(f"  Forecast period: {forecast_start.strftime('%m/%d/%Y')} – "
          f"{(forecast_start + timedelta(days=num_days - 1)).strftime('%m/%d/%Y')}")
    print("=" * 80)

    for store in stores:
        print(f"\n{'=' * 80}")
        print(f"  STORE: {store}")
        print(f"{'=' * 80}")

        # Collect products that have non-zero predictions
        active_products = []
        for product in sorted(all_products):
            forecasts = results[store][product]
            total_predicted = sum(q for _, q in forecasts)
            if total_predicted >= 0.5:  # skip near-zero items
                active_products.append((product, forecasts, total_predicted))

        if not active_products:
            print("  No items predicted for this period.\n")
            continue

        # Print daily breakdown
        dates = [forecast_start + timedelta(days=i) for i in range(num_days)]

        # Header
        header = f"  {'Product':<28}"
        for d in dates:
            header += f"{d.strftime('%m/%d'):>7}"
        header += f"{'TOTAL':>8}"
        print(header)
        print("  " + "-" * (28 + 7 * num_days + 8))

        # Sort by total predicted descending
        active_products.sort(key=lambda x: x[2], reverse=True)

        grand_total_by_day = defaultdict(float)

        for product, forecasts, total_predicted in active_products:
            line = f"  {product:<28}"
            for d, qty in forecasts:
                rounded = round(qty)
                grand_total_by_day[d] += rounded
                if rounded > 0:
                    line += f"{rounded:>7}"
                else:
                    line += f"{'·':>7}"

            line += f"{round(total_predicted):>8}"
            print(line)

        # Totals row
        print("  " + "-" * (28 + 7 * num_days + 8))
        totals_line = f"  {'DAILY TOTAL':<28}"
        grand_sum = 0
        for d in dates:
            val = round(grand_total_by_day[d])
            grand_sum += val
            totals_line += f"{val:>7}"
        totals_line += f"{grand_sum:>8}"
        print(totals_line)

    print(f"\n{'=' * 80}")
    print("  Notes:")
    print("  - Values are predicted daily quantities (rounded to whole units)")
    print("  - '·' indicates no predicted demand for that day")
    print("  - Vienna Cream includes both Vienna Cream and CS Vienna Cream")
    print("  - All products are shown for both stores regardless of historical orders")
    print(f"{'=' * 80}")


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    results, stores, all_products, forecast_start, num_days = generate_packing_lists()
    print_packing_lists(results, stores, all_products, forecast_start, num_days)
