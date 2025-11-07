"""
Visualization tools for customer trends and predictions.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


class TrendVisualizer:
    """Create visualizations for customer trends and forecasts."""

    def __init__(self):
        self.figures = []

    def plot_seasonal_trends(self, seasonal_data: pd.DataFrame,
                           save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot seasonal trend analysis.

        Args:
            seasonal_data: DataFrame with seasonal statistics
            save_path: Path to save the figure

        Returns:
            Matplotlib figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # Transaction count by season
        axes[0, 0].bar(seasonal_data['season'], seasonal_data['transaction_count'],
                      color='skyblue', edgecolor='black')
        axes[0, 0].set_title('Transactions by Season', fontsize=14, fontweight='bold')
        axes[0, 0].set_xlabel('Season')
        axes[0, 0].set_ylabel('Transaction Count')
        axes[0, 0].tick_params(axis='x', rotation=45)

        # Unique customers by season
        axes[0, 1].bar(seasonal_data['season'], seasonal_data['unique_customers'],
                      color='lightcoral', edgecolor='black')
        axes[0, 1].set_title('Unique Customers by Season', fontsize=14, fontweight='bold')
        axes[0, 1].set_xlabel('Season')
        axes[0, 1].set_ylabel('Unique Customers')
        axes[0, 1].tick_params(axis='x', rotation=45)

        # Average items per transaction
        axes[1, 0].bar(seasonal_data['season'], seasonal_data['avg_items_per_transaction'],
                      color='lightgreen', edgecolor='black')
        axes[1, 0].set_title('Avg Items per Transaction by Season', fontsize=14, fontweight='bold')
        axes[1, 0].set_xlabel('Season')
        axes[1, 0].set_ylabel('Avg Items')
        axes[1, 0].tick_params(axis='x', rotation=45)

        # Percentage of annual activity
        axes[1, 1].pie(seasonal_data['pct_of_annual'],
                      labels=seasonal_data['season'],
                      autopct='%1.1f%%',
                      colors=['#87CEEB', '#90EE90', '#FFD700', '#FFA07A'])
        axes[1, 1].set_title('Distribution of Annual Activity', fontsize=14, fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        self.figures.append(fig)
        return fig

    def plot_yearly_growth(self, yearly_data: pd.DataFrame,
                          save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot yearly growth trends.

        Args:
            yearly_data: DataFrame with yearly statistics
            save_path: Path to save the figure

        Returns:
            Matplotlib figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # Customer growth over years
        axes[0, 0].plot(yearly_data['year'], yearly_data['unique_customers'],
                       marker='o', linewidth=2, markersize=8, color='#2E86AB')
        axes[0, 0].set_title('Customer Growth Over Years', fontsize=14, fontweight='bold')
        axes[0, 0].set_xlabel('Year')
        axes[0, 0].set_ylabel('Unique Customers')
        axes[0, 0].grid(True, alpha=0.3)

        # Transaction growth over years
        axes[0, 1].plot(yearly_data['year'], yearly_data['transaction_count'],
                       marker='s', linewidth=2, markersize=8, color='#A23B72')
        axes[0, 1].set_title('Transaction Growth Over Years', fontsize=14, fontweight='bold')
        axes[0, 1].set_xlabel('Year')
        axes[0, 1].set_ylabel('Transaction Count')
        axes[0, 1].grid(True, alpha=0.3)

        # Year-over-year growth rates
        if 'customer_growth' in yearly_data.columns:
            growth_data = yearly_data.dropna(subset=['customer_growth'])
            axes[1, 0].bar(growth_data['year'], growth_data['customer_growth'],
                          color='green' if growth_data['customer_growth'].mean() > 0 else 'red',
                          alpha=0.7, edgecolor='black')
            axes[1, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            axes[1, 0].set_title('Year-over-Year Customer Growth Rate', fontsize=14, fontweight='bold')
            axes[1, 0].set_xlabel('Year')
            axes[1, 0].set_ylabel('Growth Rate (%)')
            axes[1, 0].grid(True, alpha=0.3)

        # Total items sold over years
        axes[1, 1].plot(yearly_data['year'], yearly_data['total_items'],
                       marker='D', linewidth=2, markersize=8, color='#F18F01')
        axes[1, 1].set_title('Total Items Sold Over Years', fontsize=14, fontweight='bold')
        axes[1, 1].set_xlabel('Year')
        axes[1, 1].set_ylabel('Total Items')
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        self.figures.append(fig)
        return fig

    def plot_product_seasonality(self, product_season_data: pd.DataFrame,
                                save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot product seasonality heatmap.

        Args:
            product_season_data: DataFrame with product-season statistics
            save_path: Path to save the figure

        Returns:
            Matplotlib figure
        """
        # Create pivot table for heatmap
        pivot_data = product_season_data.pivot(
            index='product',
            columns='season',
            values='total_sold'
        )

        # Reorder columns to match season order
        season_order = ['Winter', 'Spring', 'Summer', 'Fall']
        pivot_data = pivot_data[[col for col in season_order if col in pivot_data.columns]]

        fig, ax = plt.subplots(figsize=(12, 8))

        sns.heatmap(pivot_data, annot=True, fmt='.0f', cmap='YlOrRd',
                   linewidths=0.5, ax=ax, cbar_kws={'label': 'Total Sold'})

        ax.set_title('Product Seasonality Heatmap', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Season', fontsize=12)
        ax.set_ylabel('Product', fontsize=12)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        self.figures.append(fig)
        return fig

    def plot_customer_segments(self, segment_stats: pd.DataFrame,
                             segment_labels: Dict[int, str],
                             save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot customer segment analysis.

        Args:
            segment_stats: DataFrame with segment statistics
            segment_labels: Dictionary mapping segment IDs to labels
            save_path: Path to save the figure

        Returns:
            Matplotlib figure
        """
        # Add labels to stats
        segment_stats = segment_stats.copy()
        segment_stats['label'] = segment_stats['segment'].map(segment_labels)

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # Segment size distribution
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
        axes[0, 0].pie(segment_stats['customer_count'],
                      labels=segment_stats['label'],
                      autopct='%1.1f%%',
                      colors=colors[:len(segment_stats)],
                      startangle=90)
        axes[0, 0].set_title('Customer Segment Distribution', fontsize=14, fontweight='bold')

        # Average metrics by segment
        metrics = ['recency_days_mean', 'transaction_count_mean', 'total_items_mean']
        metric_labels = ['Recency (days)', 'Transactions', 'Total Items']

        x = np.arange(len(segment_stats))
        width = 0.25

        for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
            if metric in segment_stats.columns:
                axes[0, 1].bar(x + i * width, segment_stats[metric],
                             width, label=label, alpha=0.8)

        axes[0, 1].set_xlabel('Segment')
        axes[0, 1].set_ylabel('Average Value')
        axes[0, 1].set_title('Segment Characteristics', fontsize=14, fontweight='bold')
        axes[0, 1].set_xticks(x + width)
        axes[0, 1].set_xticklabels(segment_stats['label'], rotation=45, ha='right')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # Purchase frequency by segment
        if 'purchase_frequency_mean' in segment_stats.columns:
            axes[1, 0].barh(segment_stats['label'],
                           segment_stats['purchase_frequency_mean'],
                           color=colors[:len(segment_stats)])
            axes[1, 0].set_title('Average Purchase Frequency', fontsize=14, fontweight='bold')
            axes[1, 0].set_xlabel('Purchases per Day')
            axes[1, 0].grid(True, alpha=0.3, axis='x')

        # Product diversity by segment
        if 'product_diversity_mean' in segment_stats.columns:
            axes[1, 1].barh(segment_stats['label'],
                           segment_stats['product_diversity_mean'],
                           color=colors[:len(segment_stats)])
            axes[1, 1].set_title('Average Product Diversity', fontsize=14, fontweight='bold')
            axes[1, 1].set_xlabel('Unique Products Purchased')
            axes[1, 1].grid(True, alpha=0.3, axis='x')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        self.figures.append(fig)
        return fig

    def plot_forecast(self, historical_data: pd.DataFrame,
                     forecast_data: pd.DataFrame,
                     title: str = 'Demand Forecast',
                     save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot historical data with forecast.

        Args:
            historical_data: DataFrame with historical data
            forecast_data: DataFrame with forecast
            title: Plot title
            save_path: Path to save the figure

        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(15, 6))

        # Plot historical data
        if 'date' in historical_data.columns:
            ax.plot(historical_data['date'], historical_data.iloc[:, 1],
                   label='Historical', color='#2E86AB', linewidth=2)

        # Plot forecast
        if 'ds' in forecast_data.columns and 'yhat' in forecast_data.columns:
            ax.plot(forecast_data['ds'], forecast_data['yhat'],
                   label='Forecast', color='#F18F01', linewidth=2, linestyle='--')

            # Add confidence interval if available
            if 'yhat_lower' in forecast_data.columns and 'yhat_upper' in forecast_data.columns:
                ax.fill_between(forecast_data['ds'],
                               forecast_data['yhat_lower'],
                               forecast_data['yhat_upper'],
                               alpha=0.3, color='#F18F01', label='Confidence Interval')

        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Value', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        self.figures.append(fig)
        return fig

    def close_all(self):
        """Close all figure windows."""
        plt.close('all')
        self.figures = []
