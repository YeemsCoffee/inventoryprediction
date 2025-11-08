"""
Example: Sync data from Square API and run ML analysis.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integrations.square_connector import SquareDataConnector
from src.app import CustomerTrendApp


def main():
    """Demonstrate Square API integration."""

    print("=" * 70)
    print("SQUARE API INTEGRATION EXAMPLE")
    print("=" * 70)

    # Step 1: Setup Square connector
    print("\n📋 Step 1: Set up Square API Connection")
    print("-" * 70)
    print("\nYou need to:")
    print("1. Get your Square Access Token from: https://developer.squareup.com")
    print("2. Create a .env file in the project root with:")
    print("   SQUARE_ACCESS_TOKEN=your_token_here")
    print("\nFor testing, you can use the Square Sandbox environment.")

    # Try to connect (will fail if no token)
    try:
        connector = SquareDataConnector(environment='sandbox')

        print("\n✅ Testing connection...")
        result = connector.test_connection()

        if result['success']:
            print(f"✅ {result['message']}")
            print(f"   Locations: {result['locations']}")

            # Step 2: Fetch data
            print("\n📋 Step 2: Fetch Sales Data")
            print("-" * 70)

            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

            print(f"\nFetching data from {start_date} to {end_date}...")

            # Sync to CSV
            orders_df = connector.sync_to_csv(
                start_date=start_date,
                end_date=end_date,
                output_path='data/raw/square_sales.csv'
            )

            if orders_df is not None and not orders_df.empty:
                print(f"\n✅ Retrieved {len(orders_df)} transactions")
                print(f"\nSample data:")
                print(orders_df.head())

                # Step 3: Run ML analysis
                print("\n📋 Step 3: Run ML Analysis")
                print("-" * 70)

                app = CustomerTrendApp()
                app.load_data_from_csv('data/raw/square_sales.csv')

                report = app.generate_full_report(n_segments=4)
                app.print_summary(report)

                print("\n✅ Analysis complete! Check the reports above.")

        else:
            print(f"❌ {result['message']}")

    except ValueError as e:
        print(f"\n⚠️  {str(e)}")
        print("\nTo use Square integration:")
        print("1. Get your access token from https://developer.squareup.com")
        print("2. Create a .env file with: SQUARE_ACCESS_TOKEN=your_token")
        print("3. Run this script again")

    print("\n" + "=" * 70)
    print("For more info, see: https://developer.squareup.com/docs")
    print("=" * 70)


if __name__ == "__main__":
    main()
