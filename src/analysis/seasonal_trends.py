"""
Seasonal trend analysis for customer behavior.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats


class SeasonalTrendAnalyzer:
    """Analyze seasonal patterns in customer behavior."""

    def __init__(self, data: pd.DataFrame):
        """
        Initialize with processed customer data.

        Args:
            data: DataFrame with date, customer_id, product, amount columns
        """
        self.data = data.copy()
        if 'date' not in self.data.columns:
            raise ValueError("Data must contain 'date' column")

        self.data['date'] = pd.to_datetime(self.data['date'])
        self._add_time_features()

    def _add_time_features(self):
        """Add time-based features if not present."""
        if 'month' not in self.data.columns:
            self.data['month'] = self.data['date'].dt.month

        if 'season' not in self.data.columns:
            self.data['season'] = self.data['month'].map({
                12: 'Winter', 1: 'Winter', 2: 'Winter',
                3: 'Spring', 4: 'Spring', 5: 'Spring',
                6: 'Summer', 7: 'Summer', 8: 'Summer',
                9: 'Fall', 10: 'Fall', 11: 'Fall'
            })

        if 'quarter' not in self.data.columns:
            self.data['quarter'] = self.data['date'].dt.quarter

    def analyze_seasonal_patterns(self) -> pd.DataFrame:
        """
        Analyze overall seasonal patterns.

        Returns:
            DataFrame with seasonal statistics
        """
        seasonal_stats = self.data.groupby('season').agg({
            'customer_id': 'nunique',
            'amount': ['sum', 'mean', 'std'],
            'product': 'count'
        }).reset_index()

        seasonal_stats.columns = ['season', 'unique_customers', 'total_items',
                                 'avg_items_per_transaction', 'std_items',
                                 'transaction_count']

        # Add season order for proper sorting
        season_order = {'Winter': 1, 'Spring': 2, 'Summer': 3, 'Fall': 4}
        seasonal_stats['order'] = seasonal_stats['season'].map(season_order)
        seasonal_stats = seasonal_stats.sort_values('order').drop('order', axis=1)

        # Calculate percentage of annual activity
        total_transactions = seasonal_stats['transaction_count'].sum()
        seasonal_stats['pct_of_annual'] = (
            seasonal_stats['transaction_count'] / total_transactions * 100
        ).round(2)

        return seasonal_stats

    def analyze_product_seasonality(self) -> pd.DataFrame:
        """
        Analyze which products are popular in which seasons.

        Returns:
            DataFrame with product-season statistics
        """
        product_season = self.data.groupby(['product', 'season']).agg({
            'amount': ['sum', 'mean'],
            'customer_id': 'nunique'
        }).reset_index()

        product_season.columns = ['product', 'season', 'total_sold',
                                 'avg_per_transaction', 'unique_customers']

        # Calculate product's seasonal index (relative to average)
        product_totals = product_season.groupby('product')['total_sold'].transform('sum')
        product_season['seasonal_index'] = (
            (product_season['total_sold'] / product_totals * 4) * 100
        ).round(2)

        return product_season

    def identify_seasonal_peaks(self) -> Dict[str, Dict]:
        """
        Identify peak seasons for each product.

        Returns:
            Dictionary mapping products to their peak seasons and metrics
        """
        product_season = self.analyze_product_seasonality()

        peaks = {}
        for product in product_season['product'].unique():
            product_data = product_season[product_season['product'] == product]
            peak_season = product_data.loc[product_data['total_sold'].idxmax()]

            peaks[product] = {
                'peak_season': peak_season['season'],
                'peak_sales': int(peak_season['total_sold']),
                'seasonal_index': float(peak_season['seasonal_index']),
                'unique_customers': int(peak_season['unique_customers'])
            }

        return peaks

    def analyze_monthly_trends(self) -> pd.DataFrame:
        """
        Analyze monthly patterns across all years.

        Returns:
            DataFrame with monthly statistics
        """
        self.data['month_name'] = self.data['date'].dt.month_name()

        monthly_stats = self.data.groupby('month').agg({
            'customer_id': 'nunique',
            'amount': ['sum', 'mean'],
            'product': 'count'
        }).reset_index()

        monthly_stats.columns = ['month', 'unique_customers', 'total_items',
                                'avg_items', 'transaction_count']

        # Add month names
        month_names = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
                      5: 'May', 6: 'June', 7: 'July', 8: 'August',
                      9: 'September', 10: 'October', 11: 'November', 12: 'December'}
        monthly_stats['month_name'] = monthly_stats['month'].map(month_names)

        return monthly_stats

    def detect_seasonal_anomalies(self, threshold: float = 2.0) -> pd.DataFrame:
        """
        Detect unusual patterns in seasonal data.

        Args:
            threshold: Number of standard deviations for anomaly detection

        Returns:
            DataFrame with potential anomalies
        """
        monthly_stats = self.analyze_monthly_trends()

        # Calculate z-scores for transaction counts
        mean_transactions = monthly_stats['transaction_count'].mean()
        std_transactions = monthly_stats['transaction_count'].std()

        monthly_stats['z_score'] = (
            (monthly_stats['transaction_count'] - mean_transactions) / std_transactions
        )

        # Flag anomalies
        monthly_stats['is_anomaly'] = (
            np.abs(monthly_stats['z_score']) > threshold
        )

        anomalies = monthly_stats[monthly_stats['is_anomaly']].copy()
        anomalies['anomaly_type'] = np.where(
            anomalies['z_score'] > 0, 'Unusually High', 'Unusually Low'
        )

        return anomalies[['month_name', 'transaction_count', 'z_score', 'anomaly_type']]

    def get_seasonal_recommendations(self) -> List[Dict]:
        """
        Generate recommendations based on seasonal analysis.

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []

        # Analyze seasonal patterns
        seasonal_stats = self.analyze_seasonal_patterns()
        product_peaks = self.identify_seasonal_peaks()

        # Find strongest season
        peak_season = seasonal_stats.loc[
            seasonal_stats['transaction_count'].idxmax(), 'season'
        ]
        recommendations.append({
            'type': 'Peak Season',
            'season': peak_season,
            'recommendation': f'Stock up for {peak_season} - highest customer activity season'
        })

        # Product-specific recommendations
        for product, metrics in product_peaks.items():
            if metrics['seasonal_index'] > 150:  # 50% above average
                recommendations.append({
                    'type': 'Product Seasonality',
                    'product': product,
                    'season': metrics['peak_season'],
                    'recommendation': f'Increase {product} inventory for {metrics["peak_season"]}'
                })

        return recommendations
