"""
Example: What-If Scenario Simulator
Model business scenarios before implementing them.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import CustomerTrendApp
from src.models.scenario_simulator import ScenarioSimulator, ScenarioConfig


def main():
    """Run what-if scenario analysis."""

    print("=" * 70)
    print("WHAT-IF SCENARIO SIMULATOR")
    print("=" * 70)
    print()
    print("Model business scenarios before implementing them:")
    print("  🎯 Test promotions and discounts")
    print("  💰 Evaluate pricing changes")
    print("  📈 Forecast seasonal events")
    print("  👥 Plan staffing needs")
    print()
    print("=" * 70)
    print()

    # Load data
    print("📊 Loading data...")
    app = CustomerTrendApp()

    # Try to load Square data, fall back to sample data
    try:
        app.load_data('data/raw/square_sales.csv')
        print(f"✅ Loaded {len(app.processed_data)} transactions from Square")
    except:
        print("⚠️  No Square data found, creating sample data...")
        app.create_sample_data(n_customers=200, n_transactions=10000)

    print()

    # Initialize simulator
    simulator = ScenarioSimulator(app.processed_data)

    print("📈 Creating baseline forecast (next 30 days)...")
    baseline = simulator.create_baseline_forecast(days_ahead=30)

    baseline_revenue = baseline['revenue'].sum()
    baseline_units = baseline['units'].sum()

    print(f"   Baseline Forecast:")
    print(f"   • Total Revenue: ${baseline_revenue:,.2f}")
    print(f"   • Total Units: {baseline_units:,.0f}")
    print(f"   • Avg Daily Revenue: ${baseline_revenue/30:,.2f}")
    print()

    # SCENARIO 1: Black Friday Promotion (30% off, 2 weeks)
    print("🎯 SCENARIO 1: Black Friday Sale")
    print("   Strategy: 30% off all products for 14 days")
    print()

    black_friday_start = datetime.now() + timedelta(days=1)
    black_friday_end = black_friday_start + timedelta(days=14)

    scenario1 = ScenarioConfig(
        name="Black Friday 30% Off",
        scenario_type="promotion",
        discount_percent=30.0,
        duration_days=14,
        start_date=black_friday_start,
        end_date=black_friday_end
    )

    promo_forecast = simulator.simulate_promotion(scenario1)
    promo_revenue = promo_forecast['revenue'].sum()
    promo_units = promo_forecast['units'].sum()

    print(f"   Results:")
    print(f"   • Projected Revenue: ${promo_revenue:,.2f}")
    print(f"   • Projected Units: {promo_units:,.0f}")
    print(f"   • Revenue Impact: {(promo_revenue/baseline_revenue - 1)*100:+.1f}%")
    print(f"   • Volume Lift: {(promo_units/baseline_units - 1)*100:+.1f}%")
    print()

    # SCENARIO 2: Price Increase (10%)
    print("💰 SCENARIO 2: Menu Price Increase")
    print("   Strategy: Increase all prices by 10%")
    print()

    scenario2 = ScenarioConfig(
        name="10% Price Increase",
        scenario_type="pricing",
        price_change_percent=10.0,
        price_elasticity=-1.2  # 10% price up -> 12% volume down
    )

    pricing_forecast = simulator.simulate_pricing_change(scenario2)
    pricing_revenue = pricing_forecast['revenue'].sum()
    pricing_units = pricing_forecast['units'].sum()

    print(f"   Results:")
    print(f"   • Projected Revenue: ${pricing_revenue:,.2f}")
    print(f"   • Projected Units: {pricing_units:,.0f}")
    print(f"   • Revenue Impact: {(pricing_revenue/baseline_revenue - 1)*100:+.1f}%")
    print(f"   • Volume Change: {(pricing_units/baseline_units - 1)*100:+.1f}%")
    print()

    # SCENARIO 3: Holiday Season Demand Surge
    print("🎄 SCENARIO 3: Holiday Season Surge")
    print("   Strategy: Model 2.5x normal demand during holidays")
    print()

    holiday_start = datetime.now() + timedelta(days=15)
    holiday_end = holiday_start + timedelta(days=10)

    scenario3 = ScenarioConfig(
        name="Holiday 2.5x Surge",
        scenario_type="demand_shift",
        demand_multiplier=2.5,
        start_date=holiday_start,
        end_date=holiday_end
    )

    surge_forecast = simulator.simulate_demand_shift(scenario3)
    surge_revenue = surge_forecast['revenue'].sum()
    surge_units = surge_forecast['units'].sum()

    print(f"   Results:")
    print(f"   • Projected Revenue: ${surge_revenue:,.2f}")
    print(f"   • Projected Units: {surge_units:,.0f}")
    print(f"   • Revenue Impact: {(surge_revenue/baseline_revenue - 1)*100:+.1f}%")
    print()

    # Calculate staffing needs for holiday surge
    print("   👥 Staffing Requirements:")
    staffing = simulator.calculate_staffing_needs(surge_forecast)

    # Get peak day
    peak_day = staffing.loc[staffing['staff_count'].idxmax()]
    avg_staff = staffing['staff_count'].mean()

    print(f"   • Peak Day Staff Needed: {int(peak_day['staff_count'])} people")
    print(f"   • Average Daily Staff: {avg_staff:.1f} people")
    print(f"   • Labor Cost % of Revenue: {staffing['labor_cost_pct'].mean():.1f}%")
    print()

    # SCENARIO 4: Targeted Coffee Promotion (15% off coffee products only)
    print("☕ SCENARIO 4: Coffee-Only Flash Sale")
    print("   Strategy: 15% off coffee products for 7 days")
    print()

    # Get coffee-related products
    products = app.processed_data['product'].unique()
    coffee_products = [p for p in products if 'coffee' in p.lower() or
                      'espresso' in p.lower() or 'latte' in p.lower() or
                      'cappuccino' in p.lower()]

    if coffee_products:
        scenario4 = ScenarioConfig(
            name="Coffee Flash Sale",
            scenario_type="promotion",
            discount_percent=15.0,
            affected_products=coffee_products,
            duration_days=7
        )

        coffee_promo = simulator.simulate_promotion(scenario4)
        coffee_revenue = coffee_promo['revenue'].sum()

        print(f"   Affected Products: {', '.join(coffee_products[:3])}...")
        print(f"   • Projected Revenue: ${coffee_revenue:,.2f}")
        print(f"   • Revenue Impact: {(coffee_revenue/baseline_revenue - 1)*100:+.1f}%")
        print()
    else:
        print("   ⚠️  No coffee products found in data")
        print()

    # Compare all scenarios
    print("=" * 70)
    print("📊 SCENARIO COMPARISON")
    print("=" * 70)
    print()

    comparison = simulator.compare_scenarios([
        "Black Friday 30% Off",
        "10% Price Increase",
        "Holiday 2.5x Surge"
    ])

    print(comparison.to_string(index=False))
    print()

    # Generate recommendation
    print("=" * 70)
    print("💡 RECOMMENDATIONS")
    print("=" * 70)
    print()

    recommendation = simulator.generate_recommendation([
        "Black Friday 30% Off",
        "10% Price Increase",
        "Holiday 2.5x Surge"
    ])

    print(f"🏆 Best Scenario: {recommendation['best_scenario']}")
    print(f"   • Projected Revenue: ${recommendation['best_scenario_revenue']:,.2f}")
    print(f"   • Revenue Lift: {recommendation['best_scenario_lift']:+.1f}%")
    print()

    if 'highest_roi_scenario' in recommendation:
        print(f"💰 Highest ROI: {recommendation['highest_roi_scenario']}")
        print(f"   • Revenue Lift: {recommendation['highest_roi_lift']:+.1f}%")
        print()

    print(recommendation['summary'])
    print()

    # Visualize comparison
    print("📈 Generating visualization...")
    try:
        fig = simulator.visualize_scenario_comparison([
            "Black Friday 30% Off",
            "10% Price Increase",
            "Holiday 2.5x Surge"
        ])

        fig.write_html('scenario_comparison.html')
        print("✅ Visualization saved to: scenario_comparison.html")
        print("   Open this file in your browser to see interactive charts")
    except Exception as e:
        print(f"⚠️  Could not create visualization: {e}")

    print()
    print("=" * 70)
    print("✅ SCENARIO ANALYSIS COMPLETE")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("1. Review the comparison table above")
    print("2. Open scenario_comparison.html for interactive charts")
    print("3. Choose the best scenario for your business goals")
    print("4. Plan staffing and inventory based on projections")
    print()


if __name__ == "__main__":
    main()
