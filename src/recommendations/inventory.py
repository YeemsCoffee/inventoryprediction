"""
Automated inventory ordering recommendations using ML predictions.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class InventoryRecommendationEngine:
    """Generate intelligent inventory ordering recommendations."""

    def __init__(self, data: pd.DataFrame, forecast_data: Optional[Dict] = None):
        """
        Initialize recommendation engine.

        Args:
            data: Historical sales data
            forecast_data: ML forecast results
        """
        self.data = data.copy()
        self.forecast_data = forecast_data
        self.recommendations = []

    def calculate_safety_stock(self, product: str,
                              service_level: float = 0.95,
                              lead_time_days: int = 7) -> Dict:
        """
        Calculate safety stock levels for a product.

        Args:
            product: Product name
            service_level: Desired service level (0-1)
            lead_time_days: Supplier lead time in days

        Returns:
            Dictionary with safety stock calculations
        """
        from scipy import stats

        product_data = self.data[self.data['product'] == product]

        if product_data.empty:
            return {'error': f'No data for product: {product}'}

        # Calculate daily demand statistics
        daily_demand = product_data.groupby('date')['amount'].sum()

        mean_daily_demand = daily_demand.mean()
        std_daily_demand = daily_demand.std()

        # Z-score for service level
        z_score = stats.norm.ppf(service_level)

        # Safety stock = Z * σ * √L
        safety_stock = z_score * std_daily_demand * np.sqrt(lead_time_days)

        # Reorder point = (Average daily demand * Lead time) + Safety stock
        reorder_point = (mean_daily_demand * lead_time_days) + safety_stock

        return {
            'product': product,
            'mean_daily_demand': round(mean_daily_demand, 2),
            'std_daily_demand': round(std_daily_demand, 2),
            'safety_stock': round(safety_stock, 2),
            'reorder_point': round(reorder_point, 2),
            'service_level': service_level,
            'lead_time_days': lead_time_days
        }

    def calculate_economic_order_quantity(self, product: str,
                                         annual_demand: Optional[float] = None,
                                         order_cost: float = 50,
                                         holding_cost_pct: float = 0.25,
                                         unit_cost: float = 10) -> Dict:
        """
        Calculate Economic Order Quantity (EOQ).

        Args:
            product: Product name
            annual_demand: Annual demand (if None, estimated from data)
            order_cost: Fixed cost per order
            holding_cost_pct: Annual holding cost as % of unit cost
            unit_cost: Cost per unit

        Returns:
            Dictionary with EOQ calculations
        """
        product_data = self.data[self.data['product'] == product]

        if product_data.empty:
            return {'error': f'No data for product: {product}'}

        # Estimate annual demand if not provided
        if annual_demand is None:
            days_of_data = (product_data['date'].max() - product_data['date'].min()).days
            if days_of_data > 0:
                total_demand = product_data['amount'].sum()
                annual_demand = (total_demand / days_of_data) * 365
            else:
                annual_demand = product_data['amount'].sum()

        # Holding cost per unit per year
        holding_cost = unit_cost * holding_cost_pct

        # EOQ formula: √(2DS/H)
        # D = annual demand, S = order cost, H = holding cost
        eoq = np.sqrt((2 * annual_demand * order_cost) / holding_cost)

        # Number of orders per year
        orders_per_year = annual_demand / eoq

        # Total cost
        total_cost = (annual_demand * unit_cost) + \
                    (orders_per_year * order_cost) + \
                    ((eoq / 2) * holding_cost)

        return {
            'product': product,
            'economic_order_quantity': round(eoq, 0),
            'annual_demand': round(annual_demand, 0),
            'orders_per_year': round(orders_per_year, 1),
            'total_annual_cost': round(total_cost, 2),
            'order_frequency_days': round(365 / orders_per_year, 0)
        }

    def generate_reorder_recommendations(self,
                                        current_inventory: Dict[str, int],
                                        lead_time_days: int = 7,
                                        service_level: float = 0.95) -> List[Dict]:
        """
        Generate product reorder recommendations.

        Args:
            current_inventory: Dict mapping product names to current stock levels
            lead_time_days: Supplier lead time
            service_level: Desired service level

        Returns:
            List of recommendations
        """
        recommendations = []

        products = self.data['product'].unique()

        for product in products:
            # Calculate safety stock and reorder point
            safety_calc = self.calculate_safety_stock(
                product, service_level, lead_time_days
            )

            if 'error' in safety_calc:
                continue

            # Calculate EOQ
            eoq_calc = self.calculate_economic_order_quantity(product)

            if 'error' in eoq_calc:
                continue

            current_stock = current_inventory.get(product, 0)

            # Determine if reorder is needed
            reorder_point = safety_calc['reorder_point']
            should_reorder = current_stock <= reorder_point

            recommendation = {
                'product': product,
                'current_stock': current_stock,
                'reorder_point': reorder_point,
                'safety_stock': safety_calc['safety_stock'],
                'recommended_order_qty': eoq_calc['economic_order_quantity'],
                'should_reorder': should_reorder,
                'urgency': self._calculate_urgency(current_stock, reorder_point,
                                                   safety_calc['safety_stock']),
                'estimated_days_until_stockout': self._estimate_days_until_stockout(
                    product, current_stock
                )
            }

            if should_reorder:
                recommendations.append(recommendation)

        # Sort by urgency
        recommendations.sort(key=lambda x: x['estimated_days_until_stockout'])

        return recommendations

    def _calculate_urgency(self, current_stock: float,
                          reorder_point: float,
                          safety_stock: float) -> str:
        """Calculate urgency level."""
        if current_stock <= safety_stock:
            return 'CRITICAL'
        elif current_stock <= reorder_point:
            return 'HIGH'
        elif current_stock <= reorder_point * 1.2:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _estimate_days_until_stockout(self, product: str, current_stock: float) -> float:
        """Estimate days until stockout."""
        product_data = self.data[self.data['product'] == product]

        if product_data.empty or current_stock <= 0:
            return 0

        # Calculate average daily demand
        daily_demand = product_data.groupby('date')['amount'].sum()
        avg_daily_demand = daily_demand.mean()

        if avg_daily_demand == 0:
            return float('inf')

        return current_stock / avg_daily_demand

    def generate_seasonal_ordering_plan(self, months_ahead: int = 3) -> pd.DataFrame:
        """
        Generate seasonal ordering plan.

        Args:
            months_ahead: Number of months to plan

        Returns:
            DataFrame with seasonal ordering recommendations
        """
        # Analyze seasonal patterns
        self.data['month'] = pd.to_datetime(self.data['date']).dt.month
        self.data['season'] = self.data['month'].map({
            12: 'Winter', 1: 'Winter', 2: 'Winter',
            3: 'Spring', 4: 'Spring', 5: 'Spring',
            6: 'Summer', 7: 'Summer', 8: 'Summer',
            9: 'Fall', 10: 'Fall', 11: 'Fall'
        })

        # Calculate average demand by product and season
        seasonal_demand = self.data.groupby(['product', 'season']).agg({
            'amount': ['mean', 'std']
        }).reset_index()

        seasonal_demand.columns = ['product', 'season', 'avg_demand', 'std_demand']

        # Determine upcoming season
        current_month = datetime.now().month
        upcoming_months = [(current_month + i - 1) % 12 + 1 for i in range(1, months_ahead + 1)]

        season_map = {
            12: 'Winter', 1: 'Winter', 2: 'Winter',
            3: 'Spring', 4: 'Spring', 5: 'Spring',
            6: 'Summer', 7: 'Summer', 8: 'Summer',
            9: 'Fall', 10: 'Fall', 11: 'Fall'
        }

        upcoming_seasons = list(set([season_map[m] for m in upcoming_months]))

        # Filter to upcoming seasons
        plan = seasonal_demand[seasonal_demand['season'].isin(upcoming_seasons)].copy()

        # Calculate recommended stock levels
        plan['recommended_stock_level'] = plan['avg_demand'] * 30 + (plan['std_demand'] * 2)

        plan = plan.sort_values(['season', 'avg_demand'], ascending=[True, False])

        return plan[['product', 'season', 'avg_demand', 'recommended_stock_level']]

    def get_recommendations_summary(self, current_inventory: Dict[str, int] = None) -> Dict:
        """
        Generate comprehensive recommendations summary.

        Args:
            current_inventory: Current inventory levels

        Returns:
            Dictionary with all recommendations
        """
        if current_inventory is None:
            # Estimate current inventory as 30 days of average demand
            current_inventory = {}
            for product in self.data['product'].unique():
                product_data = self.data[self.data['product'] == product]
                daily_demand = product_data.groupby('date')['amount'].sum().mean()
                current_inventory[product] = daily_demand * 30

        reorder_recs = self.generate_reorder_recommendations(current_inventory)
        seasonal_plan = self.generate_seasonal_ordering_plan()

        return {
            'reorder_recommendations': reorder_recs,
            'critical_items': [r for r in reorder_recs if r['urgency'] == 'CRITICAL'],
            'seasonal_plan': seasonal_plan.to_dict('records'),
            'total_products_monitored': len(self.data['product'].unique()),
            'products_needing_reorder': len(reorder_recs),
            'generated_at': datetime.now().isoformat()
        }
