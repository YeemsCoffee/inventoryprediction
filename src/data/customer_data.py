"""
Customer data models and processing.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Tuple


class CustomerDataProcessor:
    """Process and prepare customer transaction data for ML analysis."""

    def __init__(self):
        self.data = None
        self.processed_data = None

    def load_data(self, filepath: str, date_column: str = 'date',
                  customer_column: str = 'customer_id',
                  amount_column: str = 'amount',
                  product_column: str = 'product') -> pd.DataFrame:
        """
        Load customer transaction data from CSV.

        Args:
            filepath: Path to CSV file
            date_column: Name of date column
            customer_column: Name of customer ID column
            amount_column: Name of amount/quantity column
            product_column: Name of product column

        Returns:
            DataFrame with loaded data
        """
        try:
            self.data = pd.read_csv(filepath)

            # Standardize column names
            self.data = self.data.rename(columns={
                date_column: 'date',
                customer_column: 'customer_id',
                amount_column: 'amount',
                product_column: 'product'
            })

            # Convert date to datetime (handle various formats including ISO8601)
            self.data['date'] = pd.to_datetime(self.data['date'], format='ISO8601')

            print(f"Loaded {len(self.data)} transactions from {filepath}")
            return self.data

        except Exception as e:
            raise ValueError(f"Error loading data: {str(e)}")

    def create_sample_data(self, n_customers: int = 100,
                          n_transactions: int = 5000,
                          start_date: str = '2020-01-01',
                          end_date: str = '2024-12-31') -> pd.DataFrame:
        """
        Create sample customer transaction data for testing.

        Args:
            n_customers: Number of unique customers
            n_transactions: Total number of transactions
            start_date: Start date for transactions
            end_date: End date for transactions

        Returns:
            DataFrame with sample data
        """
        np.random.seed(42)

        # Generate random dates
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.date_range(start, end, periods=n_transactions)
        dates = np.random.choice(dates, n_transactions, replace=True)

        # Product categories
        products = ['Coffee Beans', 'Espresso', 'Latte', 'Cappuccino',
                   'Pastries', 'Sandwiches', 'Tea', 'Merchandise']

        # Create transactions with seasonal patterns
        data = {
            'date': dates,
            'customer_id': np.random.randint(1, n_customers + 1, n_transactions),
            'product': np.random.choice(products, n_transactions),
            'amount': np.random.randint(1, 10, n_transactions),
            'price': np.round(np.random.uniform(2.5, 25.0, n_transactions), 2)
        }

        self.data = pd.DataFrame(data)
        self.data = self.data.sort_values('date').reset_index(drop=True)

        # Add seasonal patterns
        self.data = self._add_seasonal_patterns(self.data)

        print(f"Created sample data with {n_transactions} transactions for {n_customers} customers")
        return self.data

    def _add_seasonal_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add realistic seasonal patterns to the data."""
        df = df.copy()

        # Extract month
        df['month'] = df['date'].dt.month

        # Summer boost for cold drinks (June-August)
        summer_mask = df['month'].isin([6, 7, 8])
        cold_drinks = df['product'].isin(['Latte', 'Espresso'])
        df.loc[summer_mask & cold_drinks, 'amount'] *= 1.3

        # Winter boost for hot drinks (Dec-Feb)
        winter_mask = df['month'].isin([12, 1, 2])
        hot_drinks = df['product'].isin(['Coffee Beans', 'Tea', 'Cappuccino'])
        df.loc[winter_mask & hot_drinks, 'amount'] *= 1.4

        # Holiday season boost (Nov-Dec)
        holiday_mask = df['month'].isin([11, 12])
        df.loc[holiday_mask, 'amount'] *= 1.2

        df['amount'] = df['amount'].astype(int)
        df = df.drop('month', axis=1)

        return df

    def add_temporal_features(self) -> pd.DataFrame:
        """Add temporal features for ML analysis."""
        if self.data is None:
            raise ValueError("No data loaded. Call load_data() or create_sample_data() first.")

        df = self.data.copy()

        # Extract temporal features
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['day_of_week'] = df['date'].dt.dayofweek
        df['week_of_year'] = df['date'].dt.isocalendar().week
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

        # Add season
        df['season'] = df['month'].map({
            12: 'Winter', 1: 'Winter', 2: 'Winter',
            3: 'Spring', 4: 'Spring', 5: 'Spring',
            6: 'Summer', 7: 'Summer', 8: 'Summer',
            9: 'Fall', 10: 'Fall', 11: 'Fall'
        })

        self.processed_data = df
        return df

    def get_customer_metrics(self) -> pd.DataFrame:
        """Calculate key metrics per customer."""
        if self.data is None:
            raise ValueError("No data loaded.")

        metrics = self.data.groupby('customer_id').agg({
            'date': ['min', 'max', 'count'],
            'amount': ['sum', 'mean'],
            'price': ['sum', 'mean']
        }).reset_index()

        metrics.columns = ['customer_id', 'first_purchase', 'last_purchase',
                          'transaction_count', 'total_items', 'avg_items',
                          'total_revenue', 'avg_revenue']

        # Calculate customer lifetime (days)
        metrics['customer_lifetime_days'] = (
            metrics['last_purchase'] - metrics['first_purchase']
        ).dt.days

        # Calculate purchase frequency
        metrics['purchase_frequency'] = metrics['transaction_count'] / (
            metrics['customer_lifetime_days'] + 1
        )

        return metrics

    def aggregate_by_period(self, period: str = 'M') -> pd.DataFrame:
        """
        Aggregate data by time period.

        Args:
            period: Pandas period string ('D', 'W', 'M', 'Q', 'Y')

        Returns:
            Aggregated DataFrame
        """
        if self.data is None:
            raise ValueError("No data loaded.")

        df = self.data.copy()
        df = df.set_index('date')

        aggregated = df.groupby(pd.Grouper(freq=period)).agg({
            'customer_id': 'nunique',
            'amount': ['sum', 'mean'],
            'price': ['sum', 'mean'],
            'product': 'count'
        })

        aggregated.columns = ['unique_customers', 'total_items', 'avg_items',
                             'total_revenue', 'avg_revenue', 'transaction_count']

        return aggregated.reset_index()
