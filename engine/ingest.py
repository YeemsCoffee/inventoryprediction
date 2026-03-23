"""
Data ingestion layer.
Loads sales data from multiple CSV formats and normalizes into a unified DataFrame.
"""

import pandas as pd
import os
from config.products import PRODUCT_ALIASES, STORES


def _normalize_product(name: str) -> str:
    name = name.strip()
    return PRODUCT_ALIASES.get(name, name)


def load_sales_order_csv(filepath: str) -> pd.DataFrame:
    """Load the 'Gardena KTOWN Sales Order.csv' format."""
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    df = df.rename(columns={
        "CustomerName": "store",
        "ProductDescription": "product",
        "OrderDate": "date",
        "OrderQuantity": "qty",
    })
    df = df[df["store"].isin(STORES)]
    # Only include completed orders — exclude Deleted, Pending Approval, etc.
    if "OrderStatus" in df.columns:
        excluded = df[df["OrderStatus"] != "Completed"]
        if len(excluded) > 0:
            status_counts = excluded["OrderStatus"].value_counts().to_dict()
            print(f"  Filtered out non-completed orders: {status_counts}")
        df = df[df["OrderStatus"] == "Completed"]
    df["date"] = pd.to_datetime(df["date"], format="mixed")
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0)
    df["product"] = df["product"].apply(_normalize_product)
    return df[["store", "product", "date", "qty"]]


def load_sales_enquiry_csv(filepath: str) -> pd.DataFrame:
    """Load the 'SalesEnquiryList.csv' format (has a title row to skip)."""
    df = pd.read_csv(filepath, skiprows=1)
    df = df.rename(columns={
        "Customer": "store",
        "Product": "product",
        "Order Date": "date",
        "Quantity": "qty",
    })
    df = df[df["store"].isin(STORES)]
    # Only include completed orders — exclude Deleted, Pending Approval, etc.
    if "Status" in df.columns:
        excluded = df[df["Status"] != "Completed"]
        if len(excluded) > 0:
            status_counts = excluded["Status"].value_counts().to_dict()
            print(f"  Filtered out non-completed orders: {status_counts}")
        df = df[df["Status"] == "Completed"]
    df["date"] = pd.to_datetime(df["date"], format="mixed")
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0)
    df["product"] = df["product"].apply(_normalize_product)
    return df[["store", "product", "date", "qty"]]


def load_all_data(data_dir: str = ".") -> pd.DataFrame:
    """
    Auto-detect and load all CSV files in the data directory.
    Merges them into a single deduplicated DataFrame.
    """
    frames = []

    for fname in os.listdir(data_dir):
        if not fname.endswith(".csv"):
            continue
        # Skip output files
        if fname.startswith("packing_list_") or fname.startswith("forecast_accuracy"):
            continue

        filepath = os.path.join(data_dir, fname)

        try:
            # Peek at first line to detect format
            with open(filepath, "r", encoding="utf-8-sig") as f:
                first_line = f.readline()

            if "Sales Enquiry" in first_line:
                df = load_sales_enquiry_csv(filepath)
                frames.append(df)
                print(f"  Loaded {len(df)} rows from {fname} (SalesEnquiry format)")
            elif "CustomerName" in first_line or "OrderNumber" in first_line:
                df = load_sales_order_csv(filepath)
                frames.append(df)
                print(f"  Loaded {len(df)} rows from {fname} (SalesOrder format)")
            else:
                # Try SalesOrder format as fallback
                try:
                    df = load_sales_order_csv(filepath)
                    if len(df) > 0:
                        frames.append(df)
                        print(f"  Loaded {len(df)} rows from {fname} (auto-detected)")
                except Exception:
                    print(f"  Skipped {fname} (unrecognized format)")
        except Exception as e:
            print(f"  Error loading {fname}: {e}")

    if not frames:
        raise ValueError(f"No valid sales data found in {data_dir}")

    combined = pd.concat(frames, ignore_index=True)

    # Deduplicate: same store + product + date rows get summed
    # But first, drop exact duplicates (same row from overlapping files)
    combined = combined.drop_duplicates()

    return combined.sort_values("date").reset_index(drop=True)


def build_daily_demand(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate raw transactions to daily demand per store-product.
    Returns a DataFrame with columns: store, product, date, qty
    with one row per store-product-date combination,
    and fills in zeros for missing days.
    """
    daily = df.groupby(["store", "product", "date"])["qty"].sum().reset_index()

    # Build full date range
    min_date = daily["date"].min()
    max_date = daily["date"].max()
    all_dates = pd.date_range(min_date, max_date, freq="D")

    # Create full index
    stores = daily["store"].unique()
    products = daily["product"].unique()
    full_idx = pd.MultiIndex.from_product(
        [stores, products, all_dates],
        names=["store", "product", "date"]
    )

    daily = daily.set_index(["store", "product", "date"]).reindex(full_idx, fill_value=0.0).reset_index()
    return daily
