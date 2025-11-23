"""
Advanced Square data sync with flexible filtering options.
Pick and choose exactly what data to collect from Square.
"""

import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integrations.square_connector import SquareDataConnector

load_dotenv()


def sync_with_filters(
    start_date: str,
    end_date: str,
    location_names: list = None,
    products: list = None,
    exclude_products: list = None,
    customers_only: bool = False,
    guests_only: bool = False,
    min_price: float = None,
    max_price: float = None,
    output_path: str = 'data/raw/filtered_square_sales.csv'
):
    """
    Sync Square data with advanced filtering.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        location_names: List of location names to include (None = all locations)
        products: List of product names to include (None = all products)
        exclude_products: List of product names to exclude
        customers_only: Only include registered customers (exclude guests)
        guests_only: Only include guest transactions
        min_price: Minimum transaction price
        max_price: Maximum transaction price
        output_path: Where to save the filtered data
    """

    print("=" * 70)
    print("🔍 FILTERED SQUARE DATA SYNC")
    print("=" * 70)

    try:
        connector = SquareDataConnector()

        # Test connection
        result = connector.test_connection()
        if not result['success']:
            print(f"❌ {result['message']}")
            return

        print(f"✅ Connected to Square")
        print()

        # Get locations
        all_locations = connector.get_locations()
        print(f"📍 Available Locations:")
        for loc in all_locations:
            print(f"   • {loc['name']} (ID: {loc['id']})")
        print()

        # Filter by location if specified
        if location_names:
            location_ids = [
                loc['id'] for loc in all_locations
                if loc['name'] in location_names
            ]
            if not location_ids:
                print(f"⚠️  No matching locations found for: {location_names}")
                return
            print(f"🎯 Filtering by locations: {', '.join(location_names)}")
        else:
            location_ids = None
            print(f"🎯 Using all locations")

        print()
        print(f"📅 Date Range: {start_date} to {end_date}")
        print()

        # Fetch orders
        print("📡 Fetching data from Square...")
        orders_df = connector.fetch_orders(start_date, end_date, location_ids)

        if orders_df.empty:
            print("⚠️  No data found for this date range")
            return

        print(f"✅ Fetched {len(orders_df):,} initial transactions")
        print()

        # Apply filters
        print("🔍 Applying Filters:")
        print("-" * 70)

        initial_count = len(orders_df)

        # Filter by products (include specific products)
        if products:
            orders_df = orders_df[orders_df['product'].isin(products)]
            print(f"   ✓ Include products: {', '.join(products)}")
            print(f"     Remaining: {len(orders_df):,} transactions")

        # Filter by products (exclude specific products)
        if exclude_products:
            orders_df = orders_df[~orders_df['product'].isin(exclude_products)]
            print(f"   ✓ Exclude products: {', '.join(exclude_products)}")
            print(f"     Remaining: {len(orders_df):,} transactions")

        # Filter by customer type
        if customers_only:
            orders_df = orders_df[orders_df['customer_id'] != 'Guest']
            print(f"   ✓ Registered customers only")
            print(f"     Remaining: {len(orders_df):,} transactions")

        if guests_only:
            orders_df = orders_df[orders_df['customer_id'] == 'Guest']
            print(f"   ✓ Guest transactions only")
            print(f"     Remaining: {len(orders_df):,} transactions")

        # Filter by price range
        if min_price is not None:
            orders_df = orders_df[orders_df['price'] >= min_price]
            print(f"   ✓ Minimum price: ${min_price:.2f}")
            print(f"     Remaining: {len(orders_df):,} transactions")

        if max_price is not None:
            orders_df = orders_df[orders_df['price'] <= max_price]
            print(f"   ✓ Maximum price: ${max_price:.2f}")
            print(f"     Remaining: {len(orders_df):,} transactions")

        print()

        if orders_df.empty:
            print("❌ No data matches your filters!")
            return

        # Summary
        print("=" * 70)
        print("📊 FILTERED DATA SUMMARY")
        print("=" * 70)
        print(f"Original Transactions: {initial_count:,}")
        print(f"Filtered Transactions: {len(orders_df):,}")
        print(f"Reduction: {(1 - len(orders_df)/initial_count)*100:.1f}%")
        print()
        print(f"Unique Orders: {orders_df['order_id'].nunique():,}")
        print(f"Unique Customers: {orders_df['customer_id'].nunique():,}")
        print(f"Unique Products: {orders_df['product'].nunique():,}")
        print(f"Total Revenue: ${orders_df['price'].sum():,.2f}")
        print()

        # Save to CSV
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        orders_df.to_csv(output_path, index=False)

        print(f"💾 Filtered data saved to: {output_path}")
        print()

        # Show what products are included
        print("=" * 70)
        print("🛍️  PRODUCTS IN FILTERED DATA")
        print("=" * 70)
        product_summary = orders_df.groupby('product').agg({
            'amount': 'sum',
            'price': 'sum'
        }).sort_values('amount', ascending=False)

        for idx, (product, row) in enumerate(product_summary.iterrows(), 1):
            print(f"{idx:2d}. {product}")
            print(f"    Quantity: {int(row['amount']):,} | Revenue: ${row['price']:,.2f}")

        print()
        print("=" * 70)
        print("✅ SYNC COMPLETE!")
        print("=" * 70)

        return orders_df

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Sync Square data with advanced filtering',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Get last 30 days, only coffee products
  python sync_square_filtered.py --days 30 --products "Latte" "Cappuccino" "Espresso"

  # Get specific date range, exclude certain items
  python sync_square_filtered.py --start 2024-01-01 --end 2024-12-31 --exclude "Gift Card"

  # Only registered customers (no guests)
  python sync_square_filtered.py --days 90 --customers-only

  # Only guests
  python sync_square_filtered.py --days 90 --guests-only

  # Filter by price range
  python sync_square_filtered.py --days 30 --min-price 5.00 --max-price 20.00

  # Specific location only
  python sync_square_filtered.py --days 30 --locations "Main Street Store"

  # Combine multiple filters
  python sync_square_filtered.py --days 30 --products "Latte" "Mocha" --customers-only --min-price 3.00
        """
    )

    # Date options
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument('--days', type=int, help='Number of days back from today')
    date_group.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')

    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD), defaults to today')

    # Filter options
    parser.add_argument('--locations', nargs='+', help='Location names to include')
    parser.add_argument('--products', nargs='+', help='Product names to include')
    parser.add_argument('--exclude', nargs='+', help='Product names to exclude')
    parser.add_argument('--customers-only', action='store_true', help='Only registered customers')
    parser.add_argument('--guests-only', action='store_true', help='Only guest transactions')
    parser.add_argument('--min-price', type=float, help='Minimum transaction price')
    parser.add_argument('--max-price', type=float, help='Maximum transaction price')

    # Output
    parser.add_argument('--output', type=str, default='data/raw/filtered_square_sales.csv',
                       help='Output file path')

    args = parser.parse_args()

    # Calculate date range
    if args.days:
        end_date = args.end or datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    else:
        start_date = args.start
        end_date = args.end or datetime.now().strftime('%Y-%m-%d')

    # Run sync with filters
    sync_with_filters(
        start_date=start_date,
        end_date=end_date,
        location_names=args.locations,
        products=args.products,
        exclude_products=args.exclude,
        customers_only=args.customers_only,
        guests_only=args.guests_only,
        min_price=args.min_price,
        max_price=args.max_price,
        output_path=args.output
    )
