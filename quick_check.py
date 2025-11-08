"""
Quick script to check your data and identify issues
"""

import os
import pandas as pd

# Find CSV files
raw_data_path = 'data/raw'
csv_files = [f for f in os.listdir(raw_data_path) if f.endswith('.csv')]

if csv_files:
    filepath = os.path.join(raw_data_path, csv_files[0])
    print(f"📂 Analyzing: {csv_files[0]}")
    print("=" * 60)

    df = pd.read_csv(filepath)

    print("\n📊 DATA OVERVIEW:")
    print(f"  • Total rows: {len(df)}")
    print(f"  • Columns: {list(df.columns)}")

    print("\n🔍 FIRST 10 ROWS:")
    print(df.head(10))

    print("\n📋 DATA TYPES:")
    print(df.dtypes)

    print("\n📈 BASIC STATISTICS:")
    print(df.describe())

    # Try to detect date column
    print("\n🗓️ DATE COLUMN DETECTION:")
    for col in df.columns:
        if any(word in col.lower() for word in ['date', 'time', 'day']):
            print(f"  Potential date column: {col}")
            print(f"  Sample values: {df[col].head(3).tolist()}")

            # Try to convert to date
            try:
                dates = pd.to_datetime(df[col])
                print(f"  Date range: {dates.min()} to {dates.max()}")
                print(f"  Years covered: {dates.dt.year.unique().tolist()}")
            except:
                print(f"  ⚠️ Could not parse as dates")

    print("\n" + "=" * 60)
else:
    print("No CSV files found in data/raw/")
