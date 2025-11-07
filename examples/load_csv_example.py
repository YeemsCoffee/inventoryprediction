"""
Example: Load and analyze data from a CSV file.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import CustomerTrendApp


def main():
    """Load data from CSV and perform analysis."""

    app = CustomerTrendApp()

    # Load your CSV file
    # Make sure your CSV has columns: date, customer_id, product, amount, price
    csv_path = "path/to/your/data.csv"

    try:
        # Load data with custom column names if needed
        app.load_data_from_csv(
            filepath=csv_path,
            date_column='transaction_date',  # Your date column name
            customer_column='customer_id',    # Your customer column name
            amount_column='quantity',         # Your quantity column name
            product_column='product_name'     # Your product column name
        )

        # Perform seasonal analysis
        seasonal_results = app.analyze_seasonal_trends()
        print("\n📊 Seasonal Patterns:")
        print(seasonal_results['seasonal_patterns'])

        # Perform yearly analysis
        yearly_results = app.analyze_yearly_trends()
        print("\n📈 Yearly Growth:")
        print(yearly_results['yearly_growth'])

        # Segment customers
        segmentation = app.segment_customers(n_segments=4)
        print("\n👥 Customer Segments:")
        print(segmentation['segment_analysis'])

        # Forecast demand
        forecast = app.forecast_demand(periods=60, frequency='W')
        print("\n🔮 60-Week Demand Forecast created!")

        print("\n✅ Analysis complete!")

    except FileNotFoundError:
        print(f"❌ Error: CSV file not found at {csv_path}")
        print("\nTo use this example:")
        print("1. Prepare a CSV file with columns: date, customer_id, product, amount")
        print("2. Update the csv_path variable with your file path")
        print("3. Adjust column names in load_data_from_csv() if different")
        print("\nOr run demo.py to see the app with sample data!")


if __name__ == "__main__":
    main()
