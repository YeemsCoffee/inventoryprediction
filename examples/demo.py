"""
Demo script showing how to use the Customer Trend Analysis ML App.
"""

import sys
import os

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import CustomerTrendApp


def main():
    """Run a complete demonstration of the ML app."""

    # Initialize the app
    app = CustomerTrendApp()

    # Create sample data (or load from CSV)
    print("🎯 CUSTOMER TREND ANALYSIS ML APP - DEMO\n")
    app.create_sample_data(
        n_customers=150,
        n_transactions=8000,
        start_date='2020-01-01',
        end_date='2024-12-31'
    )

    # Generate comprehensive report
    report = app.generate_full_report(n_segments=4)

    # Print summary
    app.print_summary(report)

    # Display detailed insights
    print("\n" + "=" * 60)
    print("📊 DETAILED INSIGHTS")
    print("=" * 60)

    # Seasonal insights
    print("\n🌱 Top Seasonal Recommendations:")
    for i, rec in enumerate(report['seasonal_analysis']['recommendations'][:5], 1):
        print(f"{i}. [{rec.get('type', 'General')}] {rec.get('recommendation', rec)}")

    # Yearly insights
    print("\n📈 Yearly Growth Predictions:")
    predictions = report['yearly_analysis']['predictions']
    print(f"  • Next Year: {predictions.get('predicted_year')}")
    print(f"  • Predicted Customers: {predictions.get('predicted_customers')}")
    print(f"  • Predicted Transactions: {predictions.get('predicted_transactions')}")
    print(f"  • Confidence Level: {predictions.get('confidence')}")

    # Customer segments
    print("\n👥 Customer Segment Strategies:")
    for rec in report['customer_segmentation']['recommendations']:
        print(f"\n  {rec['segment_label']} ({rec['customer_count']} customers):")
        print(f"    → {rec['recommendation']}")

    # Product forecasts
    print("\n🔮 Product Demand Forecasts (Next 30 Weeks):")
    product_forecasts = report['demand_forecast']['product_forecasts']
    for product, forecast in list(product_forecasts.items())[:5]:
        avg_forecast = forecast['yhat'].mean()
        print(f"  • {product}: ~{avg_forecast:.0f} items/week (avg)")

    # Create visualizations
    print("\n" + "=" * 60)
    print("📊 CREATING VISUALIZATIONS")
    print("=" * 60)

    try:
        app.visualize_results(
            seasonal_data=report['seasonal_analysis']['seasonal_patterns'],
            yearly_data=report['yearly_analysis']['yearly_growth'],
            product_season_data=report['seasonal_analysis']['product_seasonality'],
            segment_data=report['customer_segmentation']
        )

        print("\n✅ Demo completed successfully!")
        print("\n💡 TIP: Visualizations have been generated. You can save them by")
        print("   providing a save_path parameter to visualize_results()")

    except Exception as e:
        print(f"\n⚠️  Visualization skipped: {str(e)}")
        print("   (This is normal in non-GUI environments)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
