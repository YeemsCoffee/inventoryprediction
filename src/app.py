"""
Main application interface for customer trend analysis and inventory prediction.
"""

import pandas as pd
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

from data.customer_data import CustomerDataProcessor
from analysis.seasonal_trends import SeasonalTrendAnalyzer
from analysis.yearly_trends import YearlyTrendAnalyzer
from models.forecaster import CustomerTrendForecaster
from models.segmentation import CustomerSegmentation
from visualization.charts import TrendVisualizer


class CustomerTrendApp:
    """
    Main application for analyzing customer trends and predicting inventory needs.
    """

    def __init__(self):
        """Initialize the application."""
        self.data_processor = CustomerDataProcessor()
        self.data = None
        self.processed_data = None
        self.visualizer = TrendVisualizer()

    def load_data_from_csv(self, filepath: str,
                          date_column: str = 'date',
                          customer_column: str = 'customer_id',
                          amount_column: str = 'amount',
                          product_column: str = 'product'):
        """
        Load customer data from CSV file.

        Args:
            filepath: Path to CSV file
            date_column: Name of date column
            customer_column: Name of customer ID column
            amount_column: Name of amount/quantity column
            product_column: Name of product column
        """
        print("📊 Loading data from CSV...")
        self.data = self.data_processor.load_data(
            filepath, date_column, customer_column, amount_column, product_column
        )
        self.processed_data = self.data_processor.add_temporal_features()
        print("✅ Data loaded successfully!\n")

    def create_sample_data(self, n_customers: int = 100,
                          n_transactions: int = 5000,
                          start_date: str = '2020-01-01',
                          end_date: str = '2024-12-31'):
        """
        Create sample data for testing.

        Args:
            n_customers: Number of unique customers
            n_transactions: Total number of transactions
            start_date: Start date for transactions
            end_date: End date for transactions
        """
        print("🎲 Creating sample data...")
        self.data = self.data_processor.create_sample_data(
            n_customers, n_transactions, start_date, end_date
        )
        self.processed_data = self.data_processor.add_temporal_features()
        print("✅ Sample data created successfully!\n")

    def analyze_seasonal_trends(self) -> Dict:
        """
        Analyze seasonal patterns in customer behavior.

        Returns:
            Dictionary with seasonal analysis results
        """
        if self.processed_data is None:
            raise ValueError("Load data first using load_data_from_csv or create_sample_data")

        print("🌱 Analyzing seasonal trends...")

        analyzer = SeasonalTrendAnalyzer(self.processed_data)

        results = {
            'seasonal_patterns': analyzer.analyze_seasonal_patterns(),
            'product_seasonality': analyzer.analyze_product_seasonality(),
            'seasonal_peaks': analyzer.identify_seasonal_peaks(),
            'monthly_trends': analyzer.analyze_monthly_trends(),
            'recommendations': analyzer.get_seasonal_recommendations()
        }

        print("✅ Seasonal analysis complete!\n")
        return results

    def analyze_yearly_trends(self) -> Dict:
        """
        Analyze long-term yearly trends.

        Returns:
            Dictionary with yearly analysis results
        """
        if self.processed_data is None:
            raise ValueError("Load data first")

        print("📈 Analyzing yearly trends...")

        analyzer = YearlyTrendAnalyzer(self.processed_data)

        results = {
            'yearly_growth': analyzer.analyze_yearly_growth(),
            'customer_retention': analyzer.calculate_customer_retention(),
            'customer_lifetime_value': analyzer.analyze_customer_lifetime_value(),
            'growth_trends': analyzer.identify_growth_trends(),
            'product_trends': analyzer.analyze_product_trends_over_time(),
            'predictions': analyzer.predict_next_year_metrics(),
            'recommendations': analyzer.get_yearly_recommendations()
        }

        print("✅ Yearly analysis complete!\n")
        return results

    def segment_customers(self, n_segments: int = 4) -> Dict:
        """
        Segment customers based on their behavior.

        Args:
            n_segments: Number of customer segments

        Returns:
            Dictionary with segmentation results
        """
        if self.processed_data is None:
            raise ValueError("Load data first")

        print(f"👥 Segmenting customers into {n_segments} groups...")

        segmentation = CustomerSegmentation(self.processed_data)
        segmentation.perform_kmeans_segmentation(n_clusters=n_segments)

        results = {
            'customer_features': segmentation.customer_features,
            'segment_analysis': segmentation.analyze_segments(),
            'segment_labels': segmentation.label_segments(),
            'recommendations': segmentation.get_segment_recommendations()
        }

        print("✅ Customer segmentation complete!\n")
        return results

    def forecast_demand(self, periods: int = 30, frequency: str = 'D') -> Dict:
        """
        Forecast future demand.

        Args:
            periods: Number of periods to forecast
            frequency: Forecast frequency ('D', 'W', 'M')

        Returns:
            Dictionary with forecast results
        """
        if self.processed_data is None:
            raise ValueError("Load data first")

        print(f"🔮 Forecasting demand for next {periods} {frequency}...")

        forecaster = CustomerTrendForecaster(self.processed_data)

        # Overall forecast
        overall_forecast = forecaster._simple_forecast(
            periods, 'date', 'amount', frequency
        )

        # Product-level forecasts
        product_forecasts = forecaster.forecast_demand_by_product(
            periods, 'product', frequency
        )

        results = {
            'overall_forecast': overall_forecast,
            'product_forecasts': product_forecasts
        }

        print("✅ Demand forecasting complete!\n")
        return results

    def generate_full_report(self, n_segments: int = 4) -> Dict:
        """
        Generate a comprehensive analysis report.

        Args:
            n_segments: Number of customer segments

        Returns:
            Dictionary with all analysis results
        """
        print("=" * 60)
        print("🚀 GENERATING COMPREHENSIVE CUSTOMER TREND ANALYSIS")
        print("=" * 60)
        print()

        report = {
            'data_summary': self._get_data_summary(),
            'seasonal_analysis': self.analyze_seasonal_trends(),
            'yearly_analysis': self.analyze_yearly_trends(),
            'customer_segmentation': self.segment_customers(n_segments),
            'demand_forecast': self.forecast_demand(periods=30, frequency='W')
        }

        print("=" * 60)
        print("✅ COMPREHENSIVE REPORT GENERATED SUCCESSFULLY!")
        print("=" * 60)
        print()

        return report

    def visualize_results(self, seasonal_data: pd.DataFrame = None,
                         yearly_data: pd.DataFrame = None,
                         product_season_data: pd.DataFrame = None,
                         segment_data: Dict = None,
                         save_path: Optional[str] = None):
        """
        Create visualizations for analysis results.

        Args:
            seasonal_data: Seasonal analysis DataFrame
            yearly_data: Yearly analysis DataFrame
            product_season_data: Product seasonality DataFrame
            segment_data: Segmentation results dictionary
            save_path: Base path to save figures (optional)
        """
        print("📊 Creating visualizations...")

        if seasonal_data is not None:
            self.visualizer.plot_seasonal_trends(
                seasonal_data,
                f"{save_path}_seasonal.png" if save_path else None
            )

        if yearly_data is not None:
            self.visualizer.plot_yearly_growth(
                yearly_data,
                f"{save_path}_yearly.png" if save_path else None
            )

        if product_season_data is not None:
            self.visualizer.plot_product_seasonality(
                product_season_data,
                f"{save_path}_products.png" if save_path else None
            )

        if segment_data is not None:
            self.visualizer.plot_customer_segments(
                segment_data['segment_analysis'],
                segment_data['segment_labels'],
                f"{save_path}_segments.png" if save_path else None
            )

        print("✅ Visualizations created!\n")

    def _get_data_summary(self) -> Dict:
        """Get summary statistics of the loaded data."""
        if self.data is None:
            return {}

        return {
            'total_transactions': len(self.data),
            'unique_customers': self.data['customer_id'].nunique(),
            'unique_products': self.data['product'].nunique(),
            'date_range': {
                'start': str(self.data['date'].min()),
                'end': str(self.data['date'].max())
            },
            'total_items_sold': int(self.data['amount'].sum())
        }

    def print_summary(self, report: Dict):
        """
        Print a human-readable summary of the analysis.

        Args:
            report: Full analysis report
        """
        print("\n" + "=" * 60)
        print("📋 ANALYSIS SUMMARY")
        print("=" * 60)

        # Data summary
        if 'data_summary' in report:
            print("\n📊 DATA OVERVIEW:")
            summary = report['data_summary']
            print(f"  • Total Transactions: {summary.get('total_transactions', 'N/A')}")
            print(f"  • Unique Customers: {summary.get('unique_customers', 'N/A')}")
            print(f"  • Unique Products: {summary.get('unique_products', 'N/A')}")
            print(f"  • Date Range: {summary.get('date_range', {}).get('start', 'N/A')} to {summary.get('date_range', {}).get('end', 'N/A')}")

        # Seasonal insights
        if 'seasonal_analysis' in report:
            print("\n🌱 SEASONAL INSIGHTS:")
            recommendations = report['seasonal_analysis'].get('recommendations', [])
            for rec in recommendations[:3]:
                print(f"  • {rec.get('recommendation', 'N/A')}")

        # Yearly insights
        if 'yearly_analysis' in report:
            print("\n📈 YEARLY TRENDS:")
            trends = report['yearly_analysis'].get('growth_trends', {})
            print(f"  • Customer Trend: {trends.get('customer_trend', 'N/A')}")
            print(f"  • Avg Customer Growth: {trends.get('avg_customer_growth_pct', 'N/A')}%")

        # Customer segments
        if 'customer_segmentation' in report:
            print("\n👥 CUSTOMER SEGMENTS:")
            recommendations = report['customer_segmentation'].get('recommendations', [])
            for rec in recommendations:
                print(f"  • {rec['segment_label']}: {rec['customer_count']} customers ({rec['percentage']}%)")

        print("\n" + "=" * 60 + "\n")
