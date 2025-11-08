"""
Yearly trend analysis for customer behavior.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats


class YearlyTrendAnalyzer:
    """Analyze long-term yearly trends in customer behavior."""

    def __init__(self, data: pd.DataFrame):
        """
        Initialize with customer data.

        Args:
            data: DataFrame with date, customer_id, product, amount columns
        """
        self.data = data.copy()
        if 'date' not in self.data.columns:
            raise ValueError("Data must contain 'date' column")

        self.data['date'] = pd.to_datetime(self.data['date'])
        self.data['year'] = self.data['date'].dt.year

    def analyze_yearly_growth(self) -> pd.DataFrame:
        """
        Analyze year-over-year growth metrics.

        Returns:
            DataFrame with yearly statistics and growth rates
        """
        yearly_stats = self.data.groupby('year').agg({
            'customer_id': 'nunique',
            'amount': ['sum', 'mean'],
            'product': 'count'
        }).reset_index()

        yearly_stats.columns = ['year', 'unique_customers', 'total_items',
                               'avg_items', 'transaction_count']

        # Calculate year-over-year growth
        yearly_stats['customer_growth'] = yearly_stats['unique_customers'].pct_change() * 100
        yearly_stats['revenue_growth'] = yearly_stats['total_items'].pct_change() * 100
        yearly_stats['transaction_growth'] = yearly_stats['transaction_count'].pct_change() * 100

        return yearly_stats

    def calculate_customer_retention(self) -> pd.DataFrame:
        """
        Calculate customer retention rates year-over-year.

        Returns:
            DataFrame with retention metrics
        """
        # Get customers by year
        customers_by_year = self.data.groupby('year')['customer_id'].apply(set)

        retention_data = []
        years = sorted(customers_by_year.index)

        for i in range(len(years) - 1):
            current_year = years[i]
            next_year = years[i + 1]

            current_customers = customers_by_year[current_year]
            next_customers = customers_by_year[next_year]

            retained = len(current_customers & next_customers)
            retention_rate = (retained / len(current_customers)) * 100 if len(current_customers) > 0 else 0

            retention_data.append({
                'year': current_year,
                'total_customers': len(current_customers),
                'retained_next_year': retained,
                'retention_rate': round(retention_rate, 2),
                'new_customers': len(next_customers - current_customers)
            })

        return pd.DataFrame(retention_data)

    def analyze_customer_lifetime_value(self) -> Dict:
        """
        Calculate customer lifetime value metrics.

        Returns:
            Dictionary with CLV statistics
        """
        # Calculate per-customer metrics
        customer_metrics = self.data.groupby('customer_id').agg({
            'amount': 'sum',
            'product': 'count',
            'date': ['min', 'max']
        }).reset_index()

        customer_metrics.columns = ['customer_id', 'total_items', 'transaction_count',
                                   'first_purchase', 'last_purchase']

        # Calculate lifetime in days
        customer_metrics['lifetime_days'] = (
            customer_metrics['last_purchase'] - customer_metrics['first_purchase']
        ).dt.days

        # Add price if available
        if 'price' in self.data.columns:
            revenue = self.data.groupby('customer_id')['price'].sum()
            customer_metrics = customer_metrics.merge(
                revenue.rename('total_revenue'),
                left_on='customer_id',
                right_index=True
            )
            avg_clv = customer_metrics['total_revenue'].mean()
        else:
            avg_clv = customer_metrics['total_items'].mean()

        return {
            'average_clv': round(avg_clv, 2),
            'median_clv': round(customer_metrics['total_items'].median(), 2),
            'avg_lifetime_days': round(customer_metrics['lifetime_days'].mean(), 2),
            'avg_transactions_per_customer': round(customer_metrics['transaction_count'].mean(), 2),
            'avg_items_per_customer': round(customer_metrics['total_items'].mean(), 2)
        }

    def identify_growth_trends(self) -> Dict:
        """
        Identify overall growth trends and patterns.

        Returns:
            Dictionary with trend analysis
        """
        yearly_growth = self.analyze_yearly_growth()

        if len(yearly_growth) < 2:
            return {'trend': 'Insufficient data', 'message': 'Need at least 2 years of data'}

        # Calculate average growth rates
        avg_customer_growth = yearly_growth['customer_growth'].mean()
        avg_revenue_growth = yearly_growth['revenue_growth'].mean()

        # Determine trend direction
        if avg_customer_growth > 10:
            customer_trend = 'Strong Growth'
        elif avg_customer_growth > 0:
            customer_trend = 'Moderate Growth'
        elif avg_customer_growth > -10:
            customer_trend = 'Stable/Slight Decline'
        else:
            customer_trend = 'Declining'

        # Linear regression for trend line
        years_numeric = yearly_growth['year'].values
        customers = yearly_growth['unique_customers'].values

        if len(years_numeric) >= 2:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                years_numeric, customers
            )
            trend_strength = abs(r_value)
        else:
            slope = 0
            trend_strength = 0

        return {
            'customer_trend': customer_trend,
            'avg_customer_growth_pct': round(avg_customer_growth, 2),
            'avg_revenue_growth_pct': round(avg_revenue_growth, 2),
            'trend_slope': round(slope, 2),
            'trend_strength': round(trend_strength, 2),
            'years_analyzed': len(yearly_growth)
        }

    def analyze_product_trends_over_time(self) -> pd.DataFrame:
        """
        Analyze how product popularity changes over years.

        Returns:
            DataFrame with product trends
        """
        product_yearly = self.data.groupby(['year', 'product']).agg({
            'amount': 'sum',
            'customer_id': 'nunique'
        }).reset_index()

        product_yearly.columns = ['year', 'product', 'total_sold', 'unique_customers']

        # Calculate growth for each product
        product_trends = []
        for product in product_yearly['product'].unique():
            product_data = product_yearly[product_yearly['product'] == product].sort_values('year')

            if len(product_data) >= 2:
                first_year_sales = product_data.iloc[0]['total_sold']
                last_year_sales = product_data.iloc[-1]['total_sold']
                growth = ((last_year_sales - first_year_sales) / first_year_sales * 100
                         if first_year_sales > 0 else 0)

                product_trends.append({
                    'product': product,
                    'first_year': product_data.iloc[0]['year'],
                    'last_year': product_data.iloc[-1]['year'],
                    'first_year_sales': first_year_sales,
                    'last_year_sales': last_year_sales,
                    'total_growth_pct': round(growth, 2)
                })

        return pd.DataFrame(product_trends)

    def predict_next_year_metrics(self) -> Dict:
        """
        Simple linear prediction for next year's metrics.

        Returns:
            Dictionary with predictions
        """
        yearly_growth = self.analyze_yearly_growth()

        if len(yearly_growth) < 2:
            return {'error': 'Need at least 2 years of data for prediction'}

        years = yearly_growth['year'].values
        customers = yearly_growth['unique_customers'].values
        transactions = yearly_growth['transaction_count'].values

        # Linear regression
        customer_slope, customer_intercept, _, _, _ = stats.linregress(years, customers)
        transaction_slope, transaction_intercept, _, _, _ = stats.linregress(years, transactions)

        next_year = years[-1] + 1
        predicted_customers = customer_slope * next_year + customer_intercept
        predicted_transactions = transaction_slope * next_year + transaction_intercept

        return {
            'predicted_year': int(next_year),
            'predicted_customers': int(max(0, predicted_customers)),
            'predicted_transactions': int(max(0, predicted_transactions)),
            'confidence': 'Low' if len(yearly_growth) < 3 else 'Medium' if len(yearly_growth) < 5 else 'High'
        }

    def get_yearly_recommendations(self) -> List[Dict]:
        """
        Generate recommendations based on yearly trend analysis.

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []

        # Analyze trends
        trends = self.identify_growth_trends()
        retention = self.calculate_customer_retention()
        product_trends = self.analyze_product_trends_over_time()

        # Check if we have enough data for trend analysis
        if 'avg_customer_growth_pct' not in trends:
            recommendations.append({
                'type': 'Data Availability',
                'priority': 'Info',
                'recommendation': 'Need at least 2 years of data for comprehensive yearly trend analysis'
            })
            return recommendations

        # Customer growth recommendations
        if trends['avg_customer_growth_pct'] < 0:
            recommendations.append({
                'type': 'Customer Growth',
                'priority': 'High',
                'recommendation': 'Focus on customer acquisition - experiencing decline in customer base'
            })
        elif trends['avg_customer_growth_pct'] > 15:
            recommendations.append({
                'type': 'Customer Growth',
                'priority': 'Medium',
                'recommendation': 'Strong growth - ensure inventory and capacity can meet increasing demand'
            })

        # Retention recommendations
        if not retention.empty:
            avg_retention = retention['retention_rate'].mean()
            if avg_retention < 50:
                recommendations.append({
                    'type': 'Customer Retention',
                    'priority': 'High',
                    'recommendation': f'Low retention rate ({avg_retention:.1f}%) - implement loyalty programs'
                })

        # Product trend recommendations
        if not product_trends.empty:
            declining_products = product_trends[product_trends['total_growth_pct'] < -20]
            for _, product in declining_products.iterrows():
                recommendations.append({
                    'type': 'Product Trend',
                    'product': product['product'],
                    'priority': 'Medium',
                    'recommendation': f'{product["product"]} sales declining - review or phase out'
                })

        return recommendations
