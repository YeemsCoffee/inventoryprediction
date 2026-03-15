"""
Packing list generator.
Converts raw forecasts into actionable packing lists with safety stock.
"""

import os
import csv
import numpy as np
import pandas as pd
from collections import defaultdict
from config.products import SPORADIC_PRODUCTS


def apply_safety_stock(
    predictions: dict,
    daily_demand: pd.DataFrame,
    safety_multiplier: float = 1.15,
) -> dict:
    """
    Apply safety stock adjustments to raw predictions.
    - High-variability products get extra buffer
    - Sporadic products get a minimum floor on their order days
    - All predictions get a small safety multiplier

    predictions: dict of (store, product) -> np.array of daily predictions
    Returns: adjusted dict with same structure
    """
    adjusted = {}

    for (store, product), preds in predictions.items():
        sp = daily_demand[
            (daily_demand["store"] == store) & (daily_demand["product"] == product)
        ]

        if len(sp) == 0 or sp["qty"].sum() == 0:
            adjusted[(store, product)] = preds
            continue

        # Compute variability
        nonzero = sp[sp["qty"] > 0]["qty"]
        cv = nonzero.std() / nonzero.mean() if len(nonzero) > 1 and nonzero.mean() > 0 else 0

        # Order frequency
        order_freq = (sp["qty"] > 0).mean()

        adj_preds = preds.copy()

        # Apply safety multiplier (more for volatile products)
        if cv > 1.0:
            adj_preds *= (safety_multiplier + 0.1)
        else:
            adj_preds *= safety_multiplier

        # Sporadic products: ensure a minimum on typical order days
        if product in SPORADIC_PRODUCTS and order_freq > 0.05:
            avg_order_size = nonzero.mean() if len(nonzero) > 0 else 1
            min_floor = max(1, round(avg_order_size * 0.5))
            # Apply floor on days that the model predicts > 0
            for i in range(len(adj_preds)):
                if adj_preds[i] > 0 and adj_preds[i] < min_floor:
                    adj_preds[i] = min_floor

        adjusted[(store, product)] = adj_preds

    return adjusted


def generate_packing_list_csv(
    predictions: dict,
    dates: pd.DatetimeIndex,
    stores: list,
    output_dir: str = "output",
) -> list:
    """
    Write packing list CSVs (one per store).
    Returns list of generated file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepaths = []

    for store in stores:
        # Collect products for this store
        store_products = {}
        for (s, product), preds in predictions.items():
            if s != store:
                continue
            rounded = np.round(preds).astype(int)
            total = rounded.sum()
            if total >= 1:
                store_products[product] = (rounded, total)

        # Sort by total descending
        sorted_products = sorted(store_products.items(), key=lambda x: x[1][1], reverse=True)

        date_str = dates[0].strftime("%Y-%m-%d")
        filename = f"packing_list_{store}_{date_str}.csv"
        filepath = os.path.join(output_dir, filename)

        date_headers = [d.strftime("%m/%d/%Y") for d in dates]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Product"] + date_headers + ["2-Week Total"])

            grand_total_by_day = np.zeros(len(dates))

            for product, (rounded, total) in sorted_products:
                row = [product]
                for i, val in enumerate(rounded):
                    grand_total_by_day[i] += val
                    row.append(val if val > 0 else "")
                row.append(int(total))
                writer.writerow(row)

            # Totals row
            writer.writerow([])
            totals_row = ["DAILY TOTAL"] + [int(v) for v in grand_total_by_day] + [int(grand_total_by_day.sum())]
            writer.writerow(totals_row)

        filepaths.append(filepath)
        print(f"  Saved: {filepath}")

    return filepaths


def print_packing_list(
    predictions: dict,
    dates: pd.DatetimeIndex,
    store: str,
):
    """Print a formatted packing list to stdout."""
    store_products = {}
    for (s, product), preds in predictions.items():
        if s != store:
            continue
        rounded = np.round(preds).astype(int)
        total = rounded.sum()
        if total >= 1:
            store_products[product] = (rounded, total)

    sorted_products = sorted(store_products.items(), key=lambda x: x[1][1], reverse=True)

    print(f"\n{'=' * 80}")
    print(f"  STORE: {store}")
    print(f"  Period: {dates[0].strftime('%m/%d/%Y')} - {dates[-1].strftime('%m/%d/%Y')}")
    print(f"{'=' * 80}")

    header = f"  {'Product':<28}"
    for d in dates:
        header += f"{d.strftime('%m/%d'):>7}"
    header += f"{'TOTAL':>8}"
    print(header)
    print("  " + "-" * (28 + 7 * len(dates) + 8))

    grand_total_by_day = np.zeros(len(dates))

    for product, (rounded, total) in sorted_products:
        line = f"  {product:<28}"
        for i, val in enumerate(rounded):
            grand_total_by_day[i] += val
            if val > 0:
                line += f"{val:>7}"
            else:
                line += f"{'·':>7}"
        line += f"{total:>8}"
        print(line)

    print("  " + "-" * (28 + 7 * len(dates) + 8))
    totals_line = f"  {'DAILY TOTAL':<28}"
    for v in grand_total_by_day:
        totals_line += f"{int(v):>7}"
    totals_line += f"{int(grand_total_by_day.sum()):>8}"
    print(totals_line)
