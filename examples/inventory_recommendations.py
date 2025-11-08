"""
Example: Get automated inventory ordering recommendations.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import CustomerTrendApp
from src.recommendations.inventory import InventoryRecommendationEngine


def main():
    """Demonstrate automated inventory recommendations."""

    print("=" * 70)
    print("AUTOMATED INVENTORY RECOMMENDATIONS")
    print("=" * 70)

    # Create sample data
    print("\n📊 Creating sample data...")
    app = CustomerTrendApp()
    app.create_sample_data(n_customers=150, n_transactions=8000)

    data = app.processed_data

    # Initialize recommendation engine
    recommender = InventoryRecommendationEngine(data)

    # Example current inventory levels
    current_inventory = {
        'Coffee Beans': 50,
        'Espresso': 30,
        'Latte': 25,
        'Cappuccino': 20,
        'Pastries': 15,
        'Sandwiches': 10,
        'Tea': 40,
        'Merchandise': 100
    }

    print("\n📋 Current Inventory Levels:")
    print("-" * 70)
    for product, qty in current_inventory.items():
        print(f"   {product}: {qty} units")

    # Get reorder recommendations
    print("\n📋 Generating Reorder Recommendations...")
    print("-" * 70)

    recommendations = recommender.generate_reorder_recommendations(
        current_inventory=current_inventory,
        lead_time_days=7,
        service_level=0.95
    )

    if recommendations:
        print(f"\n🚨 {len(recommendations)} products need reordering!\n")

        for rec in recommendations:
            print(f"Product: {rec['product']}")
            print(f"  Current Stock: {rec['current_stock']}")
            print(f"  Reorder Point: {rec['reorder_point']:.0f}")
            print(f"  Recommended Order: {rec['recommended_order_qty']:.0f} units")
            print(f"  Urgency: {rec['urgency']}")
            print(f"  Days Until Stockout: {rec['estimated_days_until_stockout']:.1f}")
            print("-" * 70)
    else:
        print("\n✅ All inventory levels are healthy!")

    # Calculate Economic Order Quantity
    print("\n📋 Economic Order Quantity (EOQ) Analysis...")
    print("-" * 70)

    eoq = recommender.calculate_economic_order_quantity(
        product='Coffee Beans',
        order_cost=50,  # $50 per order
        holding_cost_pct=0.25,  # 25% of unit cost
        unit_cost=15  # $15 per unit
    )

    print(f"\nEOQ for Coffee Beans:")
    print(f"  Optimal Order Quantity: {eoq['economic_order_quantity']:.0f} units")
    print(f"  Order Frequency: Every {eoq['order_frequency_days']:.0f} days")
    print(f"  Annual Orders: {eoq['orders_per_year']:.1f}")
    print(f"  Total Annual Cost: ${eoq['total_annual_cost']:,.2f}")

    # Seasonal ordering plan
    print("\n📋 Seasonal Ordering Plan...")
    print("-" * 70)

    seasonal_plan = recommender.generate_seasonal_ordering_plan(months_ahead=3)

    print(f"\nRecommended stock levels for upcoming seasons:\n")
    print(seasonal_plan.head(10))

    # Get comprehensive summary
    print("\n📋 Complete Recommendations Summary...")
    print("-" * 70)

    summary = recommender.get_recommendations_summary(current_inventory)

    print(f"\n📊 SUMMARY:")
    print(f"   Products Monitored: {summary['total_products_monitored']}")
    print(f"   Products Needing Reorder: {summary['products_needing_reorder']}")
    print(f"   Critical Items: {len(summary['critical_items'])}")

    if summary['critical_items']:
        print(f"\n⚠️  CRITICAL - Order Immediately:")
        for item in summary['critical_items']:
            print(f"   - {item['product']}: {item['recommended_order_qty']:.0f} units")

    print("\n" + "=" * 70)
    print("✅ Inventory recommendations complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
