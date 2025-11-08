"""
Script to analyze your customer data from data/raw folder
"""

import os
import sys
import pandas as pd

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import CustomerTrendApp

# Find CSV files in data/raw
raw_data_path = 'data/raw'
csv_files = [f for f in os.listdir(raw_data_path) if f.endswith('.csv')]

if not csv_files:
    print("No CSV files found in data/raw/")
    print("Please add your CSV file to the data/raw/ folder")
else:
    print(f"Found {len(csv_files)} CSV file(s):")
    for i, file in enumerate(csv_files, 1):
        print(f"  {i}. {file}")

    # Use the first CSV file
    csv_file = csv_files[0]
    filepath = os.path.join(raw_data_path, csv_file)

    print(f"\n📂 Loading: {csv_file}")
    print("=" * 60)

    # First, let's peek at the data to see column names
    print("\nFirst 5 rows of your data:")
    df = pd.read_csv(filepath)
    print(df.head())

    print("\n📋 Column names in your CSV:")
    print(df.columns.tolist())

    print("\n" + "=" * 60)
    print("\n🔧 NEXT STEPS:")
    print("\nUpdate the column names below to match your CSV:")
    print("  date_column = 'your_date_column_name'")
    print("  customer_column = 'your_customer_column_name'")
    print("  amount_column = 'your_amount_column_name'")
    print("  product_column = 'your_product_column_name'")

    # Try to auto-detect and run analysis
    print("\n" + "=" * 60)
    print("🚀 Attempting automatic analysis...")
    print("=" * 60)

    try:
        app = CustomerTrendApp()

        # Try to detect common column names
        columns = df.columns.tolist()

        # Common date column names
        date_col = None
        for col in columns:
            if any(word in col.lower() for word in ['date', 'time', 'day']):
                date_col = col
                break

        # Common customer column names
        customer_col = None
        for col in columns:
            if any(word in col.lower() for word in ['customer', 'client', 'user', 'id']):
                customer_col = col
                break

        # Common amount/quantity column names
        amount_col = None
        for col in columns:
            if any(word in col.lower() for word in ['amount', 'quantity', 'qty', 'count']):
                amount_col = col
                break

        # Common product column names
        product_col = None
        for col in columns:
            if any(word in col.lower() for word in ['product', 'item', 'name', 'sku']):
                product_col = col
                break

        print(f"\n🔍 Detected columns:")
        print(f"  Date: {date_col}")
        print(f"  Customer: {customer_col}")
        print(f"  Amount: {amount_col}")
        print(f"  Product: {product_col}")

        if date_col and customer_col and amount_col and product_col:
            print("\n✅ All required columns detected! Running analysis...")

            app.load_data_from_csv(
                filepath=filepath,
                date_column=date_col,
                customer_column=customer_col,
                amount_column=amount_col,
                product_column=product_col
            )

            # Generate full report
            report = app.generate_full_report(n_segments=4)

            # Print summary
            app.print_summary(report)

            print("\n" + "=" * 60)
            print("✅ ANALYSIS COMPLETE!")
            print("=" * 60)

        else:
            print("\n⚠️  Could not auto-detect all columns.")
            print("Please update this script with your exact column names.")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nPlease check your data format and try again.")
