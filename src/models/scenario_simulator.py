"""
What-If Scenario Simulator for business decision modeling.
Test promotions, pricing changes, demand shifts before implementing them.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import plotly.graph_objects as go
from plotly.subplots import make_subplots


@dataclass
class ScenarioConfig:
    """Configuration for a what-if scenario."""
    name: str
    scenario_type: str  # 'promotion', 'pricing', 'demand_shift', 'seasonal_event'

    # Promotion parameters
    discount_percent: float = 0.0
    affected_products: Optional[List[str]] = None
    duration_days: int = 7

    # Pricing parameters
    price_change_percent: float = 0.0
    price_elasticity: float = -1.5  # Typical elasticity: -1.5 means 10% price increase = 15% demand decrease

    # Demand shift parameters
    demand_multiplier: float = 1.0

    # Staffing parameters
    staff_cost_per_hour: float = 15.0
    hours_per_shift: float = 8.0

    # Time range
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ScenarioSimulator:
    """Simulate business scenarios and forecast their impact."""

    def __init__(self, historical_data: pd.DataFrame):
        """
        Initialize simulator with historical data.

        Args:
            historical_data: DataFrame with historical sales/transactions
        """
        self.data = historical_data.copy()
        self.baseline_forecast = None
        self.scenarios = {}

    def create_baseline_forecast(self, days_ahead: int = 30) -> pd.DataFrame:
        """
        Create baseline forecast from historical data.

        Args:
            days_ahead: Number of days to forecast

        Returns:
            DataFrame with baseline forecast
        """
        # Calculate daily averages by product
        daily_stats = self.data.groupby([self.data['date'].dt.date, 'product']).agg({
            'amount': 'sum',
            'price': 'sum'
        }).reset_index()

        daily_stats.columns = ['date', 'product', 'units', 'revenue']
        daily_stats['date'] = pd.to_datetime(daily_stats['date'])

        # Get recent 30-day average per product
        recent_cutoff = daily_stats['date'].max() - timedelta(days=30)
        recent_data = daily_stats[daily_stats['date'] >= recent_cutoff]

        product_averages = recent_data.groupby('product').agg({
            'units': 'mean',
            'revenue': 'mean'
        }).reset_index()

        # Generate forecast dates
        last_date = self.data['date'].max()
        forecast_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=days_ahead,
            freq='D'
        )

        # Create baseline forecast
        forecast_rows = []
        for date in forecast_dates:
            for _, product_row in product_averages.iterrows():
                # Add day-of-week seasonality
                dow_factor = self._get_day_of_week_factor(date)

                forecast_rows.append({
                    'date': date,
                    'product': product_row['product'],
                    'units': product_row['units'] * dow_factor,
                    'revenue': product_row['revenue'] * dow_factor,
                    'scenario': 'baseline'
                })

        self.baseline_forecast = pd.DataFrame(forecast_rows)
        return self.baseline_forecast

    def _get_day_of_week_factor(self, date: datetime) -> float:
        """Get demand multiplier based on day of week."""
        # Weekend typically has higher traffic
        dow = date.weekday()
        if dow in [5, 6]:  # Saturday, Sunday
            return 1.3
        elif dow == 4:  # Friday
            return 1.15
        elif dow == 0:  # Monday
            return 0.9
        else:
            return 1.0

    def simulate_promotion(self, config: ScenarioConfig) -> pd.DataFrame:
        """
        Simulate a promotional campaign.

        Args:
            config: Scenario configuration

        Returns:
            DataFrame with promotion scenario forecast
        """
        if self.baseline_forecast is None:
            self.create_baseline_forecast()

        scenario_data = self.baseline_forecast.copy()

        # Filter to promotion date range
        if config.start_date and config.end_date:
            promo_mask = (
                (scenario_data['date'] >= config.start_date) &
                (scenario_data['date'] <= config.end_date)
            )
        else:
            # Default: first N days
            promo_dates = scenario_data['date'].unique()[:config.duration_days]
            promo_mask = scenario_data['date'].isin(promo_dates)

        # Filter to affected products
        if config.affected_products:
            product_mask = scenario_data['product'].isin(config.affected_products)
        else:
            product_mask = pd.Series([True] * len(scenario_data))

        # Apply promotion effects
        discount_factor = 1 - (config.discount_percent / 100)

        # Promotions typically increase volume but decrease per-unit revenue
        volume_lift = self._calculate_promotion_lift(config.discount_percent)

        scenario_data.loc[promo_mask & product_mask, 'units'] *= volume_lift
        scenario_data.loc[promo_mask & product_mask, 'revenue'] *= (volume_lift * discount_factor)

        scenario_data['scenario'] = config.name
        scenario_data['promotion_active'] = promo_mask & product_mask

        self.scenarios[config.name] = scenario_data
        return scenario_data

    def _calculate_promotion_lift(self, discount_percent: float) -> float:
        """
        Calculate expected volume lift from a promotion.
        Based on typical promotional elasticity.

        Args:
            discount_percent: Discount percentage

        Returns:
            Volume multiplier (e.g., 1.4 = 40% increase)
        """
        # Typical promotional elasticity: 20% discount -> 40-50% volume lift
        # Using logarithmic function to model diminishing returns
        if discount_percent == 0:
            return 1.0

        # Model: lift = 1 + (discount_pct / 100) * 2.5 * (1 - discount_pct/200)
        # This gives realistic lifts with diminishing returns
        base_lift = (discount_percent / 100) * 2.5
        diminishing_factor = 1 - (discount_percent / 200)

        return 1.0 + (base_lift * diminishing_factor)

    def simulate_pricing_change(self, config: ScenarioConfig) -> pd.DataFrame:
        """
        Simulate a pricing change scenario.

        Args:
            config: Scenario configuration

        Returns:
            DataFrame with pricing scenario forecast
        """
        if self.baseline_forecast is None:
            self.create_baseline_forecast()

        scenario_data = self.baseline_forecast.copy()

        # Filter to affected products
        if config.affected_products:
            product_mask = scenario_data['product'].isin(config.affected_products)
        else:
            product_mask = pd.Series([True] * len(scenario_data))

        # Apply price elasticity
        # Elasticity formula: % change in quantity = elasticity * % change in price
        price_change_factor = config.price_change_percent / 100
        volume_change = config.price_elasticity * price_change_factor

        volume_multiplier = 1 + volume_change
        price_multiplier = 1 + price_change_factor

        scenario_data.loc[product_mask, 'units'] *= volume_multiplier
        scenario_data.loc[product_mask, 'revenue'] *= (volume_multiplier * price_multiplier)

        scenario_data['scenario'] = config.name
        scenario_data['price_change'] = product_mask

        self.scenarios[config.name] = scenario_data
        return scenario_data

    def simulate_demand_shift(self, config: ScenarioConfig) -> pd.DataFrame:
        """
        Simulate a demand shift (e.g., seasonal event, marketing campaign).

        Args:
            config: Scenario configuration

        Returns:
            DataFrame with demand shift scenario
        """
        if self.baseline_forecast is None:
            self.create_baseline_forecast()

        scenario_data = self.baseline_forecast.copy()

        # Filter to event date range
        if config.start_date and config.end_date:
            event_mask = (
                (scenario_data['date'] >= config.start_date) &
                (scenario_data['date'] <= config.end_date)
            )
        else:
            # Default: entire forecast period
            event_mask = pd.Series([True] * len(scenario_data))

        # Filter to affected products
        if config.affected_products:
            product_mask = scenario_data['product'].isin(config.affected_products)
        else:
            product_mask = pd.Series([True] * len(scenario_data))

        # Apply demand multiplier
        scenario_data.loc[event_mask & product_mask, 'units'] *= config.demand_multiplier
        scenario_data.loc[event_mask & product_mask, 'revenue'] *= config.demand_multiplier

        scenario_data['scenario'] = config.name
        scenario_data['event_active'] = event_mask & product_mask

        self.scenarios[config.name] = scenario_data
        return scenario_data

    def calculate_staffing_needs(self, scenario_data: pd.DataFrame,
                                units_per_staff_hour: float = 20.0) -> pd.DataFrame:
        """
        Calculate staffing requirements based on forecasted demand.

        Args:
            scenario_data: Forecasted demand data
            units_per_staff_hour: Expected productivity (units handled per staff hour)

        Returns:
            DataFrame with staffing recommendations
        """
        daily_demand = scenario_data.groupby('date').agg({
            'units': 'sum',
            'revenue': 'sum'
        }).reset_index()

        # Assuming 8-hour shifts, calculate staff needed
        daily_demand['staff_hours_needed'] = daily_demand['units'] / units_per_staff_hour
        daily_demand['staff_count'] = np.ceil(daily_demand['staff_hours_needed'] / 8)

        # Add cost estimates
        staff_cost = 15.0  # Default hourly rate
        daily_demand['labor_cost'] = daily_demand['staff_hours_needed'] * staff_cost
        daily_demand['labor_cost_pct'] = (
            daily_demand['labor_cost'] / daily_demand['revenue'] * 100
        )

        return daily_demand

    def compare_scenarios(self, scenario_names: List[str]) -> pd.DataFrame:
        """
        Compare multiple scenarios side-by-side.

        Args:
            scenario_names: List of scenario names to compare

        Returns:
            DataFrame with comparison metrics
        """
        if self.baseline_forecast is None:
            raise ValueError("Create baseline forecast first")

        # Add baseline to comparison
        all_scenarios = ['baseline'] + scenario_names

        comparison = []

        for scenario_name in all_scenarios:
            if scenario_name == 'baseline':
                data = self.baseline_forecast
            else:
                if scenario_name not in self.scenarios:
                    print(f"Warning: Scenario '{scenario_name}' not found, skipping")
                    continue
                data = self.scenarios[scenario_name]

            total_units = data['units'].sum()
            total_revenue = data['revenue'].sum()
            avg_daily_revenue = data.groupby('date')['revenue'].sum().mean()

            comparison.append({
                'scenario': scenario_name,
                'total_units': total_units,
                'total_revenue': total_revenue,
                'avg_daily_revenue': avg_daily_revenue,
                'revenue_vs_baseline': 0.0 if scenario_name == 'baseline' else
                    ((total_revenue / self.baseline_forecast['revenue'].sum() - 1) * 100)
            })

        return pd.DataFrame(comparison)

    def visualize_scenario_comparison(self, scenario_names: List[str]) -> go.Figure:
        """
        Create visualization comparing scenarios.

        Args:
            scenario_names: List of scenario names to visualize

        Returns:
            Plotly figure
        """
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Daily Revenue Comparison',
                'Total Revenue by Scenario',
                'Daily Units Comparison',
                'Revenue Impact vs Baseline'
            ),
            specs=[[{"type": "scatter"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "bar"}]]
        )

        # Add baseline
        all_scenarios = ['baseline'] + scenario_names

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

        for i, scenario_name in enumerate(all_scenarios):
            if scenario_name == 'baseline':
                data = self.baseline_forecast
            else:
                if scenario_name not in self.scenarios:
                    continue
                data = self.scenarios[scenario_name]

            # Daily revenue over time
            daily_revenue = data.groupby('date')['revenue'].sum().reset_index()
            fig.add_trace(
                go.Scatter(
                    x=daily_revenue['date'],
                    y=daily_revenue['revenue'],
                    name=scenario_name,
                    line=dict(color=colors[i % len(colors)]),
                    legendgroup=scenario_name
                ),
                row=1, col=1
            )

            # Daily units over time
            daily_units = data.groupby('date')['units'].sum().reset_index()
            fig.add_trace(
                go.Scatter(
                    x=daily_units['date'],
                    y=daily_units['units'],
                    name=scenario_name,
                    line=dict(color=colors[i % len(colors)]),
                    showlegend=False,
                    legendgroup=scenario_name
                ),
                row=2, col=1
            )

        # Total revenue comparison
        comparison_df = self.compare_scenarios(scenario_names)

        fig.add_trace(
            go.Bar(
                x=comparison_df['scenario'],
                y=comparison_df['total_revenue'],
                name='Total Revenue',
                showlegend=False,
                marker_color=colors[:len(comparison_df)]
            ),
            row=1, col=2
        )

        # Revenue impact vs baseline
        impact_df = comparison_df[comparison_df['scenario'] != 'baseline']

        fig.add_trace(
            go.Bar(
                x=impact_df['scenario'],
                y=impact_df['revenue_vs_baseline'],
                name='% Change',
                showlegend=False,
                marker_color=['green' if x > 0 else 'red'
                             for x in impact_df['revenue_vs_baseline']]
            ),
            row=2, col=2
        )

        # Update layout
        fig.update_xaxes(title_text="Date", row=1, col=1)
        fig.update_xaxes(title_text="Scenario", row=1, col=2)
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_xaxes(title_text="Scenario", row=2, col=2)

        fig.update_yaxes(title_text="Revenue ($)", row=1, col=1)
        fig.update_yaxes(title_text="Revenue ($)", row=1, col=2)
        fig.update_yaxes(title_text="Units", row=2, col=1)
        fig.update_yaxes(title_text="% Change", row=2, col=2)

        fig.update_layout(
            title_text="What-If Scenario Comparison",
            height=800,
            showlegend=True
        )

        return fig

    def generate_recommendation(self, scenario_names: List[str]) -> Dict:
        """
        Generate recommendations based on scenario comparison.

        Args:
            scenario_names: List of scenarios to evaluate

        Returns:
            Dictionary with recommendations
        """
        comparison = self.compare_scenarios(scenario_names)

        # Find best scenario by revenue
        best_revenue = comparison.loc[comparison['total_revenue'].idxmax()]

        # Find scenario with best revenue lift
        scenarios_only = comparison[comparison['scenario'] != 'baseline']
        if len(scenarios_only) > 0:
            best_lift = scenarios_only.loc[scenarios_only['revenue_vs_baseline'].idxmax()]
        else:
            best_lift = None

        recommendation = {
            'best_scenario': best_revenue['scenario'],
            'best_scenario_revenue': best_revenue['total_revenue'],
            'best_scenario_lift': best_revenue['revenue_vs_baseline'],
            'summary': f"Based on the analysis, '{best_revenue['scenario']}' shows the highest "
                      f"potential revenue of ${best_revenue['total_revenue']:,.2f}",
            'all_scenarios': comparison.to_dict('records')
        }

        if best_lift is not None:
            recommendation['highest_roi_scenario'] = best_lift['scenario']
            recommendation['highest_roi_lift'] = best_lift['revenue_vs_baseline']

        return recommendation
