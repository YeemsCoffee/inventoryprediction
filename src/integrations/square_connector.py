"""
Square API integration for automatic sales data collection.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()

# Business timezone (PST/PDT)
PST = ZoneInfo('America/Los_Angeles')


class SquareDataConnector:
    """Connect to Square API and fetch sales, inventory, and customer data."""

    def __init__(self, access_token: Optional[str] = None, environment: str = 'production'):
        """
        Initialize Square API connector.

        Args:
            access_token: Square Access Token (if None, reads from environment)
            environment: 'production' or 'sandbox'
        """
        self.access_token = access_token or os.getenv('SQUARE_ACCESS_TOKEN')
        if not self.access_token:
            raise ValueError("Square Access Token is required. Set SQUARE_ACCESS_TOKEN environment variable.")

        self.environment = environment
        self.base_url = (
            'https://connect.squareup.com'
            if environment == 'production'
            else 'https://connect.squareupsandbox.com'
        )

        self.headers = {
            'Square-Version': '2024-01-18',
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def test_connection(self) -> Dict:
        """
        Test the API connection.

        Returns:
            Dictionary with connection status
        """
        try:
            response = requests.get(
                f'{self.base_url}/v2/locations',
                headers=self.headers
            )

            if response.status_code == 200:
                locations = response.json().get('locations', [])
                return {
                    'success': True,
                    'message': f'Connected successfully! Found {len(locations)} location(s)',
                    'locations': [loc.get('name') for loc in locations]
                }
            else:
                return {
                    'success': False,
                    'message': f'Connection failed: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection error: {str(e)}'
            }

    def get_locations(self) -> List[Dict]:
        """
        Get all Square locations.

        Returns:
            List of location dictionaries
        """
        response = requests.get(
            f'{self.base_url}/v2/locations',
            headers=self.headers
        )
        response.raise_for_status()

        locations = response.json().get('locations', [])
        return [{
            'id': loc['id'],
            'name': loc.get('name'),
            'address': loc.get('address', {}).get('address_line_1'),
            'status': loc.get('status')
        } for loc in locations]

    def fetch_orders(self, start_date: str, end_date: str,
                    location_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fetch orders/transactions from Square.

        Args:
            start_date: Start date (YYYY-MM-DD) in PST timezone
            end_date: End date (YYYY-MM-DD) in PST timezone
            location_ids: List of location IDs (if None, fetches from all locations)

        Returns:
            DataFrame with order data (timestamps converted to PST)

        Note:
            - Input dates are treated as PST (business timezone)
            - Dates are converted to UTC for Square API calls
            - Returned timestamps are converted back to PST for storage
        """
        if location_ids is None:
            locations = self.get_locations()
            location_ids = [loc['id'] for loc in locations]

        all_orders = []

        # Convert dates to RFC 3339 format
        # IMPORTANT: Treat input dates as PST (business timezone), then convert to UTC for Square API
        start_dt_naive = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt_naive = datetime.strptime(end_date, '%Y-%m-%d')

        # Make timezone-aware in PST
        start_dt_pst = start_dt_naive.replace(tzinfo=PST)
        end_dt_pst = end_dt_naive.replace(tzinfo=PST)

        # Convert to UTC for Square API (Square expects UTC timestamps)
        start_dt_utc = start_dt_pst.astimezone(ZoneInfo('UTC'))
        end_dt_utc = end_dt_pst.astimezone(ZoneInfo('UTC'))

        query = {
            'location_ids': location_ids,
            'query': {
                'filter': {
                    'date_time_filter': {
                        'created_at': {
                            'start_at': start_dt_utc.isoformat(),
                            'end_at': end_dt_utc.isoformat()
                        }
                    }
                }
            }
        }

        cursor = None
        while True:
            if cursor:
                query['cursor'] = cursor

            response = requests.post(
                f'{self.base_url}/v2/orders/search',
                headers=self.headers,
                json=query,
                timeout=60  # 60 second timeout
            )
            response.raise_for_status()

            data = response.json()
            orders = data.get('orders', [])

            if not orders:
                break

            all_orders.extend(orders)

            cursor = data.get('cursor')
            if not cursor:
                break

        return self._parse_orders_to_dataframe(all_orders)

    def _parse_orders_to_dataframe(self, orders: List[Dict]) -> pd.DataFrame:
        """Parse Square orders into a clean DataFrame."""
        rows = []

        for order in orders:
            order_id = order.get('id')
            # Parse timestamp from Square (Square returns PST timestamps, not UTC!)
            created_at_raw = pd.to_datetime(order.get('created_at'))
            # Square already returns PST - just ensure it's timezone-aware
            if created_at_raw.tz is None:
                # If naive, it's already PST from Square
                created_at = created_at_raw.tz_localize(PST)
            else:
                # If timezone-aware, keep as-is (Square sends PST)
                created_at = created_at_raw
            customer_id = order.get('customer_id', 'Guest')
            location_id = order.get('location_id')

            # Get line items
            line_items = order.get('line_items', [])

            for item in line_items:
                # Determine product name - handle null cases intelligently
                product_name = item.get('name')
                item_type = item.get('item_type', 'ITEM')  # ITEM, CUSTOM_AMOUNT, GIFT_CARD

                # If no name, create one based on context
                if not product_name or not product_name.strip():
                    # Check if it's a custom amount
                    if item_type == 'CUSTOM_AMOUNT':
                        product_name = 'Custom Amount'
                    # Check for modifiers (tips, service charges)
                    elif item.get('modifiers'):
                        product_name = 'Modified Item'
                    # Check if it has catalog object (should have name but doesn't)
                    elif item.get('catalog_object_id'):
                        product_name = 'Catalog Item (Unnamed)'
                    # Fallback
                    else:
                        product_name = 'Unknown Product'

                # Extract modifiers
                modifiers = item.get('modifiers', [])
                modifier_names = []
                modifier_details = []

                for mod in modifiers:
                    mod_name = mod.get('name', '')
                    if mod_name:
                        modifier_names.append(mod_name)
                        # Include modifier price if applicable
                        mod_total = mod.get('total_money', {})
                        mod_amount = mod_total.get('amount', 0)
                        if mod_amount and mod_amount > 0:
                            mod_price = float(mod_amount) / 100
                            modifier_details.append(f"{mod_name} (+${mod_price:.2f})")
                        else:
                            modifier_details.append(mod_name)

                # Create combined product name with modifiers
                if modifier_names:
                    product_with_modifiers = f"{product_name} ({', '.join(modifier_names)})"
                    modifiers_str = ', '.join(modifier_details)
                else:
                    product_with_modifiers = product_name
                    modifiers_str = ''

                # Safe extraction with None handling
                quantity_raw = item.get('quantity', 1)
                quantity = int(quantity_raw) if quantity_raw is not None else 1

                # Handle total_money which might be None or have None amount
                total_money = item.get('total_money', {}) or {}
                amount = total_money.get('amount')
                price = float(amount) / 100 if amount is not None else 0.0

                rows.append({
                    'order_id': order_id,
                    'date': created_at,
                    'customer_id': customer_id,
                    'location_id': location_id,
                    'product': product_with_modifiers,  # Combined name with modifiers
                    'base_product': product_name,  # Original product name
                    'modifiers': modifiers_str,  # Modifier details
                    'item_type': item_type,
                    'quantity': quantity,
                    'price': price,
                    'category': item.get('catalog_object_id'),
                    'variation_id': item.get('catalog_object_id')
                })

        df = pd.DataFrame(rows)

        if not df.empty:
            # Rename columns to match our ML app format
            df = df.rename(columns={
                'quantity': 'amount',
                'product': 'product'
            })

        return df

    def fetch_customers(self) -> pd.DataFrame:
        """
        Fetch customer data from Square.

        Returns:
            DataFrame with customer information
        """
        all_customers = []
        cursor = None

        while True:
            params = {}
            if cursor:
                params['cursor'] = cursor

            response = requests.get(
                f'{self.base_url}/v2/customers',
                headers=self.headers,
                params=params
            )
            response.raise_for_status()

            data = response.json()
            customers = data.get('customers', [])

            if not customers:
                break

            all_customers.extend(customers)

            cursor = data.get('cursor')
            if not cursor:
                break

        return self._parse_customers_to_dataframe(all_customers)

    def _parse_customers_to_dataframe(self, customers: List[Dict]) -> pd.DataFrame:
        """Parse Square customers into a DataFrame."""
        rows = []

        for customer in customers:
            rows.append({
                'customer_id': customer.get('id'),
                'given_name': customer.get('given_name'),
                'family_name': customer.get('family_name'),
                'email': customer.get('email_address'),
                'phone': customer.get('phone_number'),
                'created_at': pd.to_datetime(customer.get('created_at')),
                'updated_at': pd.to_datetime(customer.get('updated_at'))
            })

        return pd.DataFrame(rows)

    def fetch_inventory(self) -> pd.DataFrame:
        """
        Fetch inventory/catalog data from Square.

        Returns:
            DataFrame with product catalog
        """
        all_items = []
        cursor = None

        while True:
            params = {'types': 'ITEM'}
            if cursor:
                params['cursor'] = cursor

            response = requests.get(
                f'{self.base_url}/v2/catalog/list',
                headers=self.headers,
                params=params
            )
            response.raise_for_status()

            data = response.json()
            objects = data.get('objects', [])

            if not objects:
                break

            all_items.extend(objects)

            cursor = data.get('cursor')
            if not cursor:
                break

        return self._parse_catalog_to_dataframe(all_items)

    def _parse_catalog_to_dataframe(self, items: List[Dict]) -> pd.DataFrame:
        """Parse Square catalog items into a DataFrame."""
        rows = []

        for item in items:
            if item.get('type') != 'ITEM':
                continue

            item_data = item.get('item_data', {})
            rows.append({
                'item_id': item.get('id'),
                'name': item_data.get('name'),
                'description': item_data.get('description'),
                'category_id': item_data.get('category_id'),
                'available': not item_data.get('is_deleted', False),
                'variations': len(item_data.get('variations', []))
            })

        return pd.DataFrame(rows)

    def sync_to_csv(self, start_date: str, end_date: str,
                   output_path: str = 'data/raw/square_sales.csv'):
        """
        Sync Square data to CSV file for ML analysis.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            output_path: Where to save the CSV file
        """
        print(f"📡 Fetching data from Square ({start_date} to {end_date})...")

        # Fetch orders
        orders_df = self.fetch_orders(start_date, end_date)

        if orders_df.empty:
            print("⚠️  No orders found in the specified date range.")
            return

        print(f"✅ Fetched {len(orders_df)} transactions")

        # Save to CSV
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        orders_df.to_csv(output_path, index=False)

        print(f"💾 Data saved to {output_path}")

        return orders_df

    def get_summary_stats(self, start_date: str, end_date: str) -> Dict:
        """
        Get summary statistics from Square data.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary with summary statistics
        """
        orders_df = self.fetch_orders(start_date, end_date)

        if orders_df.empty:
            return {'message': 'No data found'}

        return {
            'total_transactions': len(orders_df['order_id'].unique()),
            'total_items_sold': orders_df['amount'].sum(),
            'total_revenue': orders_df['price'].sum(),
            'unique_customers': orders_df['customer_id'].nunique(),
            'unique_products': orders_df['product'].nunique(),
            'date_range': {
                'start': orders_df['date'].min().strftime('%Y-%m-%d'),
                'end': orders_df['date'].max().strftime('%Y-%m-%d')
            },
            'average_order_value': orders_df.groupby('order_id')['price'].sum().mean()
        }
