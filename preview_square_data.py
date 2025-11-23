"""
Quick script to preview Square data without saving to database.
Shows you exactly what data is being pulled.
"""

import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integrations.square_connector import SquareDataConnector

load_dotenv()

def preview_square_data(days=7):
    """Preview recent Square data."""

    print("=" * 70)
    print("📊 SQUARE DATA PREVIEW")
    print("=" * 70)

    try:
        connector = SquareDataConnector()

        # Test connection
        result = connector.test_connection()
        if not result['success']:
            print(f"❌ {result['message']}")
            return

        print(f"✅ Connected to Square")
        print(f"   Locations: {result['locations']}")
        print()

        # Get last N days
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        print(f"📅 Fetching last {days} days of data...")
        print(f"   From: {start_date}")
        print(f"   To: {end_date}")
        print()

        # Fetch orders
        orders_df = connector.fetch_orders(start_date, end_date)

        if orders_df.empty:
            print("⚠️  No data found for this date range")
            return

        # Show summary
        print("=" * 70)
        print("📊 DATA SUMMARY")
        print("=" * 70)
        print(f"Total Transactions: {len(orders_df):,}")
        print(f"Unique Orders: {orders_df['order_id'].nunique():,}")
        print(f"Unique Customers: {orders_df['customer_id'].nunique():,}")
        print(f"Unique Products: {orders_df['product'].nunique():,}")
        print(f"Total Revenue: ${orders_df['price'].sum():,.2f}")
        print(f"Date Range: {orders_df['date'].min()} to {orders_df['date'].max()}")
        print()

        # Show column names
        print("=" * 70)
        print("📋 COLUMNS IN DATA")
        print("=" * 70)
        for col in orders_df.columns:
            print(f"  • {col}")
        print()

        # Show sample data
        print("=" * 70)
        print("📝 SAMPLE DATA (First 10 Rows)")
        print("=" * 70)
        print(orders_df.head(10).to_string())
        print()

        # Show product breakdown
        print("=" * 70)
        print("🛍️  TOP 10 PRODUCTS")
        print("=" * 70)
        top_products = orders_df.groupby('product').agg({
            'amount': 'sum',
            'price': 'sum'
        }).sort_values('amount', ascending=False).head(10)

        for idx, (product, row) in enumerate(top_products.iterrows(), 1):
            print(f"{idx:2d}. {product}")
            print(f"    Quantity: {int(row['amount']):,} | Revenue: ${row['price']:,.2f}")
        print()

        # Show customer breakdown
        print("=" * 70)
        print("👥 CUSTOMER BREAKDOWN")
        print("=" * 70)
        guest_count = (orders_df['customer_id'] == 'Guest').sum()
        registered_count = (orders_df['customer_id'] != 'Guest').sum()
        print(f"Guest Transactions: {guest_count:,} ({guest_count/len(orders_df)*100:.1f}%)")
        print(f"Registered Customer Transactions: {registered_count:,} ({registered_count/len(orders_df)*100:.1f}%)")
        print()

        # Option to save
        print("=" * 70)
        print("💾 SAVE OPTIONS")
        print("=" * 70)
        print("To save this data, run one of:")
        print("  python examples/square_integration_example.py")
        print("  python sync_custom_range.py", start_date, end_date)

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Preview Square data')
    parser.add_argument('--days', type=int, default=7, help='Number of days to preview (default: 7)')

    args = parser.parse_args()

    preview_square_data(days=args.days)
