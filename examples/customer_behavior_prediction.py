"""
Example: Predict customer behavior - churn, CLV, next purchase.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import CustomerTrendApp
from src.models.customer_behavior import CustomerBehaviorPredictor


def main():
    """Demonstrate customer behavior predictions."""

    print("=" * 70)
    print("CUSTOMER BEHAVIOR PREDICTION")
    print("=" * 70)

    # Create sample data
    print("\n📊 Creating sample data...")
    app = CustomerTrendApp()
    app.create_sample_data(n_customers=200, n_transactions=10000)

    data = app.processed_data

    # Initialize predictor
    predictor = CustomerBehaviorPredictor(data)

    # Predict churn
    print("\n📋 Predicting Customer Churn...")
    print("-" * 70)

    churn_predictions = predictor.predict_churn(threshold_days=60, train_model=True)

    high_risk = churn_predictions[churn_predictions['churn_risk'] == 'High']
    print(f"\n⚠️  Found {len(high_risk)} high-risk customers")
    print(f"\nTop 5 customers at risk of churning:")
    print(churn_predictions.nlargest(5, 'churn_probability')[[
        'customer_id', 'churn_probability', 'churn_risk', 'date_recency'
    ]])

    # Predict Customer Lifetime Value
    print("\n📋 Calculating Customer Lifetime Value (CLV)...")
    print("-" * 70)

    clv = predictor.calculate_customer_lifetime_value(months_ahead=12)

    print(f"\n💎 Top 10 customers by predicted CLV:")
    print(clv.nlargest(10, 'predicted_clv')[[
        'customer_id', 'predicted_clv', 'clv_segment'
    ]])

    # Find at-risk high-value customers
    print("\n📋 Identifying At-Risk High-Value Customers...")
    print("-" * 70)

    at_risk_hv = predictor.get_at_risk_high_value_customers()

    if len(at_risk_hv) > 0:
        print(f"\n🚨 {len(at_risk_hv)} high-value customers at risk!")
        print("\nTop 5 to focus on:")
        print(at_risk_hv.head()[[
            'customer_id', 'predicted_clv', 'churn_probability', 'churn_risk'
        ]])
    else:
        print("\n✅ No high-value customers at risk!")

    # Predict next purchase
    print("\n📋 Predicting Next Purchase Timing...")
    print("-" * 70)

    next_purchase = predictor.predict_next_purchase()

    likely_soon = next_purchase[next_purchase['likely_to_purchase_soon'] == True]
    print(f"\n🎯 {len(likely_soon)} customers likely to purchase soon")
    print(f"\nSample predictions:")
    print(next_purchase.head()[[
        'customer_id', 'avg_days_between_purchases', 'expected_next_purchase_date'
    ]])

    # Get comprehensive insights
    print("\n📋 Generating Comprehensive Insights...")
    print("-" * 70)

    insights = predictor.get_customer_insights_summary()

    print(f"\n📊 CUSTOMER INSIGHTS SUMMARY:")
    print(f"   Total Customers: {insights['total_customers']}")
    print(f"   Active Customers: {insights['active_customers']}")
    print(f"   At-Risk Customers: {insights['at_risk_customers']}")
    print(f"   High-Value Customers: {insights['high_value_customers']}")
    print(f"   At-Risk High-Value: {insights['at_risk_high_value']}")
    print(f"   Avg Customer Lifetime: {insights['avg_customer_lifetime_days']:.0f} days")
    print(f"   Total Predicted CLV: ${insights['predicted_clv_total']:,.2f}")

    print("\n" + "=" * 70)
    print("✅ Customer behavior prediction complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
