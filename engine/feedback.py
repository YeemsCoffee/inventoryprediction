"""
Feedback loop system.
Compares past forecasts against actual sales and adjusts future predictions.
Stores accuracy history for continuous improvement.
"""

import json
import os
import tempfile
import numpy as np
import pandas as pd
from datetime import datetime
from engine.backtest import compute_metrics


FEEDBACK_FILE = "output/forecast_history.json"


def load_feedback_history(filepath: str = FEEDBACK_FILE) -> list:
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"WARNING: {filepath} is corrupted, starting fresh history")
                return []
    return []


def save_feedback_history(history: list, filepath: str = FEEDBACK_FILE):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    # Write to temp file first, then rename to avoid corruption from Ctrl+C
    dir_name = os.path.dirname(filepath) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(history, f, indent=2, default=str)
        os.replace(tmp_path, filepath)
    except BaseException:
        os.unlink(tmp_path)
        raise


def record_forecast(
    store: str,
    product: str,
    forecast_date: str,
    predicted_qty: float,
    model_version: str = "v2",
    filepath: str = FEEDBACK_FILE,
):
    """Record a single forecast (loads/saves each call — prefer record_forecasts_batch)."""
    record_forecasts_batch(
        [(store, product, forecast_date, predicted_qty)],
        model_version=model_version,
        filepath=filepath,
    )


def record_forecasts_batch(
    entries: list,
    model_version: str = "v2",
    filepath: str = FEEDBACK_FILE,
):
    """Record multiple forecasts in a single load/save cycle.

    entries: list of (store, product, forecast_date, predicted_qty) tuples.
    """
    history = load_feedback_history(filepath)
    now = datetime.now().isoformat()

    # Build lookup of existing entries to avoid duplicates
    existing = set()
    for h in history:
        existing.add((h["store"], h["product"], h["date"]))

    for store, product, forecast_date, predicted_qty in entries:
        key = (store, product, forecast_date)
        if key in existing:
            # Update the existing entry with the new prediction
            for h in history:
                if h["store"] == store and h["product"] == product and h["date"] == forecast_date:
                    h["predicted"] = round(predicted_qty)
                    h["recorded_at"] = now
                    break
        else:
            history.append({
                "store": store,
                "product": product,
                "date": forecast_date,
                "predicted": round(predicted_qty),
                "actual": None,
                "model_version": model_version,
                "recorded_at": now,
            })
            existing.add(key)
    save_feedback_history(history, filepath)


def update_actuals(
    actuals_df: pd.DataFrame,
    filepath: str = FEEDBACK_FILE,
):
    """
    Match actual sales data against stored forecasts.
    actuals_df should have columns: store, product, date, qty
    """
    history = load_feedback_history(filepath)
    if not history:
        return 0

    updated = 0
    for entry in history:
        if entry["actual"] is not None:
            continue

        match = actuals_df[
            (actuals_df["store"] == entry["store"]) &
            (actuals_df["product"] == entry["product"]) &
            (actuals_df["date"].dt.strftime("%Y-%m-%d") == entry["date"])
        ]

        if len(match) > 0:
            entry["actual"] = float(match["qty"].sum())
        else:
            # No sales record means zero sold
            entry["actual"] = 0.0
        entry["error"] = round(entry["predicted"] - entry["actual"], 2)
        updated += 1

    save_feedback_history(history, filepath)
    return updated


def compute_correction_factors(filepath: str = FEEDBACK_FILE) -> dict:
    """
    Compute per-store-product correction factors based on historical forecast errors.
    Returns dict of (store, product) -> correction_multiplier.

    If model consistently over-forecasts by 20%, multiplier = 0.83
    If model consistently under-forecasts by 30%, multiplier = 1.30
    """
    history = load_feedback_history(filepath)

    # Only use entries where we have actuals
    completed = [h for h in history if h.get("actual") is not None and h["actual"] > 0]

    if not completed:
        return {}

    corrections = {}
    # Group by store-product
    groups = {}
    for entry in completed:
        key = (entry["store"], entry["product"])
        if key not in groups:
            groups[key] = []
        groups[key].append(entry)

    for (store, product), entries in groups.items():
        if len(entries) < 3:
            # Need at least 3 data points for a meaningful correction
            continue

        actuals = np.array([e["actual"] for e in entries])
        predicted = np.array([e["predicted"] for e in entries])

        # Compute bias ratio
        total_actual = actuals.sum()
        total_predicted = predicted.sum()

        if total_predicted > 0:
            ratio = total_actual / total_predicted
            # Clamp to prevent wild swings
            ratio = np.clip(ratio, 0.5, 2.0)
            corrections[(store, product)] = round(ratio, 3)

    return corrections


def generate_feedback_report(filepath: str = FEEDBACK_FILE) -> str:
    """Generate a report on forecast accuracy from the feedback loop."""
    history = load_feedback_history(filepath)
    completed = [h for h in history if h.get("actual") is not None]

    if not completed:
        return "No feedback data available yet. Run forecasts and then update with actuals."

    lines = []
    lines.append("=" * 70)
    lines.append("  FEEDBACK LOOP REPORT")
    lines.append("=" * 70)
    lines.append(f"  Total forecasts recorded: {len(history)}")
    lines.append(f"  With actual data: {len(completed)}")
    lines.append(f"  Pending actuals: {len(history) - len(completed)}")

    actuals = np.array([e["actual"] for e in completed])
    predicted = np.array([e["predicted"] for e in completed])

    metrics = compute_metrics(actuals, predicted)
    lines.append(f"\n  Overall Accuracy:")
    lines.append(f"    MAE:    {metrics['mae']}")
    lines.append(f"    WMAPE:  {metrics['wmape']}%")
    lines.append(f"    Bias:   {metrics['bias']:+.2f}")

    corrections = compute_correction_factors(filepath)
    if corrections:
        lines.append(f"\n  Correction Factors Applied:")
        for (store, product), factor in sorted(corrections.items()):
            direction = "scale up" if factor > 1 else "scale down"
            lines.append(f"    {store} / {product}: x{factor} ({direction})")

    lines.append(f"\n{'=' * 70}")
    return "\n".join(lines)


def export_feedback_to_excel(
    output_path: str = "output/feedback_report.xlsx",
    filepath: str = FEEDBACK_FILE,
):
    """Export all feedback history to a formatted Excel workbook."""
    history = load_feedback_history(filepath)
    if not history:
        return None

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    completed = [h for h in history if h.get("actual") is not None]

    if not completed:
        # No actuals yet — write a placeholder sheet so the file isn't corrupted
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            pd.DataFrame({"Status": ["No actual sales data recorded yet. Run --update-actuals first."]}).to_excel(
                writer, sheet_name="Accuracy by Day", index=False
            )
        return output_path

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Group entries by date
        by_date = {}
        for entry in completed:
            by_date.setdefault(entry["date"], []).append(entry)

        # One tab per date, sorted chronologically
        for date_str in sorted(by_date.keys()):
            entries = by_date[date_str]
            rows = []
            for entry in sorted(entries, key=lambda e: (e["store"], e["product"])):
                predicted = entry["predicted"]
                actual = entry["actual"]
                denom = max(predicted, actual)
                if denom > 0:
                    accuracy_pct = round((1 - abs(predicted - actual) / denom) * 100, 1)
                else:
                    accuracy_pct = None  # both zero, no activity
                rows.append({
                    "Store": entry["store"],
                    "Product": entry["product"],
                    "Predicted": int(predicted),
                    "Actual": int(actual),
                    "Accuracy (%)": accuracy_pct,
                })

            day_df = pd.DataFrame(rows)
            # Use MM-DD format for tab name (sheet names max 31 chars)
            tab_name = pd.Timestamp(date_str).strftime("%m-%d")
            day_df.to_excel(writer, sheet_name=tab_name, index=False)

        # Final tab: Accuracy Summary across all dates
        summary_rows = []
        groups = {}
        for entry in completed:
            key = (entry["store"], entry["product"])
            groups.setdefault(key, []).append(entry)

        for (store, product), entries in sorted(groups.items()):
            actuals_arr = np.array([e["actual"] for e in entries])
            predicted_arr = np.array([e["predicted"] for e in entries])
            metrics = compute_metrics(actuals_arr, predicted_arr)
            corrections = compute_correction_factors(filepath)
            factor = corrections.get((store, product), 1.0)
            summary_rows.append({
                "Store": store,
                "Product": product,
                "Forecasts": len(entries),
                "MAE": metrics["mae"],
                "WMAPE (%)": metrics["wmape"],
                "Bias": round(metrics["bias"], 2),
                "Correction Factor": factor,
            })

        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_excel(writer, sheet_name="Accuracy Summary", index=False)

        # Auto-fit column widths
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col_cells in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col_cells)
                header_len = len(str(col_cells[0].value or ""))
                width = max(max_len, header_len) + 2
                ws.column_dimensions[col_cells[0].column_letter].width = width

    return output_path
