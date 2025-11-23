"""
Load and analyze Square CSV reports (Item Sales, Detailed Sales, etc.)
Handles Square dashboard exports with modifiers and detailed item info.
"""

import sys
import os
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import CustomerTrendApp


def load_square_report(csv_path: str, report_type: str = 'auto'):
    """
    Load Square report CSV and prepare for ML analysis.

    Args:
        csv_path: Path to Square CSV export
        report_type: Type of report ('item_sales', 'detailed_sales', 'auto')

    Returns:
        DataFrame formatted for ML analysis
    """

    print("=" * 70)
    print("📊 SQUARE REPORT LOADER")
    print("=" * 70)

    try:
        # Load CSV
        print(f"\n📂 Loading: {csv_path}")
        df = pd.read_csv(csv_path)

        print(f"✅ Loaded {len(df):,} rows")
        print()

        # Show columns
        print("📋 Columns in CSV:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i:2d}. {col}")
        print()

        # Auto-detect report type
        if report_type == 'auto':
            if 'Item' in df.columns or 'Item Name' in df.columns:
                report_type = 'item_sales'
                print("🔍 Detected: Item Sales Report")
            elif 'Product' in df.columns:
                report_type = 'detailed_sales'
                print("🔍 Detected: Detailed Sales Report")
            else:
                print("⚠️  Unknown report type, will attempt auto-mapping")
        print()

        # Map Square report columns to ML format
        print("🔄 Converting to ML format...")

        # Common column mappings from Square reports
        column_mapping = {
            # Date columns
            'Date': 'date',
            'Transaction Date': 'date',
            'Time': 'date',
            'Created At': 'date',

            # Product/Item columns
            'Item': 'product',
            'Item Name': 'product',
            'Product': 'product',
            'Product Name': 'product',

            # Quantity columns
            'Qty': 'amount',
            'Quantity': 'amount',
            'Qty Sold': 'amount',

            # Price columns
            'Gross Sales': 'price',
            'Net Sales': 'price',
            'Total': 'price',
            'Amount': 'price',
            'Price': 'price',

            # Customer columns
            'Customer': 'customer_id',
            'Customer Name': 'customer_id',
            'Customer ID': 'customer_id',

            # Location columns
            'Location': 'location_id',
            'Location Name': 'location_id',

            # Category columns
            'Category': 'category',
            'Item Category': 'category',

            # Modifier columns
            'Modifiers': 'modifiers',
            'Modifier': 'modifiers',
            'Modifier Name': 'modifiers',
        }

        # Rename columns
        df_renamed = df.copy()
        for old_col, new_col in column_mapping.items():
            if old_col in df_renamed.columns:
                df_renamed = df_renamed.rename(columns={old_col: new_col})
                print(f"   ✓ Mapped: {old_col} → {new_col}")

        print()

        # Ensure required columns exist
        required_cols = ['date', 'product', 'amount']
        missing_cols = [col for col in required_cols if col not in df_renamed.columns]

        if missing_cols:
            print(f"⚠️  Missing required columns: {missing_cols}")
            print("\n💡 Manual mapping needed. Current columns:")
            print(df.columns.tolist())
            print("\nPlease specify column mappings:")
            return None

        # Handle modifiers (combine with product name if present)
        if 'modifiers' in df_renamed.columns:
            print("🎯 Combining items with modifiers...")
            # Create combined product name: "Product (Modifier)"
            mask = df_renamed['modifiers'].notna() & (df_renamed['modifiers'] != '')
            df_renamed.loc[mask, 'product'] = (
                df_renamed.loc[mask, 'product'] + ' (' +
                df_renamed.loc[mask, 'modifiers'] + ')'
            )
            print(f"   ✓ Combined {mask.sum():,} items with modifiers")
            print()

        # Parse dates
        if 'date' in df_renamed.columns:
            df_renamed['date'] = pd.to_datetime(df_renamed['date'], errors='coerce')

        # Handle customer ID (use 'Guest' for empty)
        if 'customer_id' in df_renamed.columns:
            df_renamed['customer_id'] = df_renamed['customer_id'].fillna('Guest')
        else:
            df_renamed['customer_id'] = 'Guest'

        # Ensure numeric types
        if 'amount' in df_renamed.columns:
            df_renamed['amount'] = pd.to_numeric(df_renamed['amount'], errors='coerce')

        if 'price' in df_renamed.columns:
            # Remove currency symbols and convert
            if df_renamed['price'].dtype == 'object':
                df_renamed['price'] = df_renamed['price'].str.replace('$', '').str.replace(',', '')
            df_renamed['price'] = pd.to_numeric(df_renamed['price'], errors='coerce')

        # Drop rows with missing critical data
        df_clean = df_renamed.dropna(subset=['date', 'product'])

        print("=" * 70)
        print("📊 PROCESSED DATA SUMMARY")
        print("=" * 70)
        print(f"Total Rows: {len(df_clean):,}")
        print(f"Unique Products: {df_clean['product'].nunique():,}")

        if 'customer_id' in df_clean.columns:
            print(f"Unique Customers: {df_clean['customer_id'].nunique():,}")

        if 'amount' in df_clean.columns:
            print(f"Total Items Sold: {df_clean['amount'].sum():,.0f}")

        if 'price' in df_clean.columns:
            print(f"Total Revenue: ${df_clean['price'].sum():,.2f}")

        if 'date' in df_clean.columns:
            print(f"Date Range: {df_clean['date'].min()} to {df_clean['date'].max()}")

        print()

        # Show top products (with modifiers)
        if 'amount' in df_clean.columns:
            print("=" * 70)
            print("🛍️  TOP 15 PRODUCTS (Including Modifiers)")
            print("=" * 70)

            top_products = df_clean.groupby('product').agg({
                'amount': 'sum',
                'price': 'sum' if 'price' in df_clean.columns else 'count'
            }).sort_values('amount', ascending=False).head(15)

            for idx, (product, row) in enumerate(top_products.iterrows(), 1):
                qty = int(row['amount'])
                if 'price' in df_clean.columns:
                    print(f"{idx:2d}. {product}")
                    print(f"    Qty: {qty:,} | Revenue: ${row['price']:,.2f}")
                else:
                    print(f"{idx:2d}. {product} (Qty: {qty:,})")

        print()

        return df_clean

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def analyze_square_report(csv_path: str):
    """Load Square report and run ML analysis."""

    # Load and process report
    df = load_square_report(csv_path)

    if df is None or df.empty:
        print("❌ Could not load data")
        return

    # Save processed data
    processed_path = 'data/raw/processed_square_report.csv'
    os.makedirs(os.path.dirname(processed_path), exist_ok=True)
    df.to_csv(processed_path, index=False)
    print(f"💾 Processed data saved to: {processed_path}")
    print()

    # Run ML analysis
    print("=" * 70)
    print("🤖 RUNNING ML ANALYSIS")
    print("=" * 70)

    try:
        app = CustomerTrendApp()
        app.data = df

        # Generate full report
        report = app.generate_full_report(n_segments=4)

        # Print summary
        app.print_summary(report)

        print()
        print("=" * 70)
        print("✅ ANALYSIS COMPLETE!")
        print("=" * 70)

    except Exception as e:
        print(f"⚠️  ML Analysis error: {str(e)}")
        print("Data was still processed and saved successfully.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Load and analyze Square CSV reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
How to use:

1. Export report from Square Dashboard:
   - Go to Square Dashboard → Reports → Sales
   - Select "Item Sales" or "Detailed Sales Report"
   - Set date range
   - Click Export → Download CSV

2. Run this script:
   python load_square_report.py path/to/your/report.csv

Examples:
  python load_square_report.py data/raw/item_sales.csv
  python load_square_report.py ~/Downloads/square_report_2024.csv

The script will:
  - Auto-detect report type
  - Combine items with modifiers
  - Format data for ML analysis
  - Run complete trend analysis
  - Show seasonal patterns, customer segments, forecasts
        """
    )

    parser.add_argument('csv_file', help='Path to Square CSV export')
    parser.add_argument('--report-type', choices=['auto', 'item_sales', 'detailed_sales'],
                       default='auto', help='Type of Square report')

    args = parser.parse_args()

    # Check if file exists
    if not os.path.exists(args.csv_file):
        print(f"❌ File not found: {args.csv_file}")
        sys.exit(1)

    # Analyze the report
    analyze_square_report(args.csv_file)
