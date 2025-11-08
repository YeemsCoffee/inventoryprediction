# Advanced Features Guide

This guide covers the advanced ML and deep learning features of the Business Intelligence Platform.

## 🚀 Table of Contents

1. [Square API Integration](#square-api-integration)
2. [Deep Learning Forecasting](#deep-learning-forecasting)
3. [Customer Behavior Prediction](#customer-behavior-prediction)
4. [Interactive Dashboard](#interactive-dashboard)
5. [Automated Inventory Recommendations](#automated-inventory-recommendations)

---

## 📡 Square API Integration

Automatically sync your Point-of-Sale data from Square.

### Setup

1. **Get Square Access Token:**
   - Go to https://developer.squareup.com
   - Create an application
   - Copy your Access Token

2. **Create `.env` file:**
```bash
# Create .env in project root
echo "SQUARE_ACCESS_TOKEN=your_access_token_here" > .env
```

3. **Test Connection:**
```python
from src.integrations.square_connector import SquareDataConnector

connector = SquareDataConnector()
result = connector.test_connection()
print(result)
```

### Sync Sales Data

```python
from src.integrations.square_connector import SquareDataConnector
from src.app import CustomerTrendApp

# Sync last 90 days
connector = SquareDataConnector()
orders_df = connector.sync_to_csv(
    start_date='2024-01-01',
    end_date='2024-03-31',
    output_path='data/raw/square_sales.csv'
)

# Run ML analysis
app = CustomerTrendApp()
app.load_data_from_csv('data/raw/square_sales.csv')
report = app.generate_full_report()
```

### Automated Daily Sync

```python
import schedule
import time

def daily_sync():
    connector = SquareDataConnector()
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    connector.sync_to_csv(yesterday, today)
    print(f"✅ Synced data for {yesterday}")

# Schedule daily at 1 AM
schedule.every().day.at("01:00").do(daily_sync)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 🧠 Deep Learning Forecasting

Advanced forecasting with LSTM neural networks and XGBoost.

### LSTM (Long Short-Term Memory) Forecasting

```python
from src.models.advanced_forecaster import AdvancedForecaster

forecaster = AdvancedForecaster(your_data)

# Train LSTM model
lstm_result = forecaster.train_lstm_forecast(
    date_column='date',
    value_column='amount',
    lookback=30,        # Use 30 days of history
    epochs=50,          # Training iterations
    frequency='D'       # Daily data
)

# Generate forecast
forecast = forecaster.forecast_lstm(periods=30, lookback=30)
print(forecast)
```

**When to use LSTM:**
- Complex seasonal patterns
- Long-term dependencies
- Non-linear trends
- You have lots of data (>1 year)

### XGBoost Forecasting

```python
# Train XGBoost model
xgb_result = forecaster.train_xgboost_forecast(
    date_column='date',
    value_column='amount',
    frequency='D'
)

# View feature importance
print(xgb_result['feature_importance'])
```

**When to use XGBoost:**
- Feature-rich data
- Need interpretability
- Medium-sized datasets
- Want faster training

### Ensemble Forecasting

Combine multiple models for best accuracy:

```python
ensemble_forecast = forecaster.ensemble_forecast(
    periods=30,
    models=['prophet', 'xgboost', 'lstm']
)
```

**Benefits:**
- More robust predictions
- Reduces single-model bias
- Better confidence intervals

---

## 👥 Customer Behavior Prediction

Predict churn, lifetime value, and next purchase timing.

### Churn Prediction

```python
from src.models.customer_behavior import CustomerBehaviorPredictor

predictor = CustomerBehaviorPredictor(your_data)

# Predict which customers will churn
churn_pred = predictor.predict_churn(
    threshold_days=60,    # 60 days inactive = churned
    train_model=True
)

# Find high-risk customers
high_risk = churn_pred[churn_pred['churn_risk'] == 'High']
print(f"At-risk customers: {len(high_risk)}")
```

**Use Cases:**
- Send re-engagement campaigns
- Offer retention incentives
- Prioritize customer support
- Prevent revenue loss

### Customer Lifetime Value (CLV) Prediction

```python
# Predict CLV for next 12 months
clv = predictor.calculate_customer_lifetime_value(months_ahead=12)

# Find your most valuable customers
top_customers = predictor.identify_high_value_customers(top_pct=0.2)
print(top_customers)
```

**Use Cases:**
- Prioritize marketing spend
- VIP customer programs
- Personalized offers
- Resource allocation

### Next Purchase Prediction

```python
next_purchase = predictor.predict_next_purchase()

# Customers likely to buy soon
ready_to_buy = next_purchase[
    next_purchase['likely_to_purchase_soon'] == True
]
```

**Use Cases:**
- Timely marketing emails
- Inventory planning
- Personalized recommendations
- Win-back campaigns

### Combined Insights

```python
# Find high-value customers at risk
at_risk_vip = predictor.get_at_risk_high_value_customers()

# Full customer insights summary
insights = predictor.get_customer_insights_summary()
print(insights)
```

---

## 📊 Interactive Dashboard

Tableau/Power BI-style web dashboard with real-time analytics.

### Launch Dashboard

```python
from src.dashboard.app import create_dashboard

# With your data
dashboard = create_dashboard('data/raw/sales.csv')

# Or with sample data
dashboard = create_dashboard()

# Run server
dashboard.run(host='127.0.0.1', port=8050)
```

Then open: http://127.0.0.1:8050

### Dashboard Features

**📊 Overview Tab:**
- Real-time KPIs (Revenue, Customers, AOV)
- Sales trends over time
- Top products
- Seasonal performance
- Customer segments visualization

**📈 Trends & Forecasts Tab:**
- 30-day demand forecast
- Yearly growth trends
- Seasonal pattern heatmap
- Product-level predictions

**👥 Customer Analysis Tab:**
- Customer segmentation (RFM)
- Churn risk analysis
- CLV distribution
- Behavior patterns

**📦 Product Insights Tab:**
- Best/worst performers
- Product seasonality
- Category analysis
- Inventory turnover

**🔮 ML Predictions Tab:**
- AI-powered forecasts
- Confidence intervals
- At-risk customer alerts
- Recommended actions

### Customization

```python
# Create custom dashboard
dashboard = BusinessIntelligenceDashboard('your_data.csv')

# Add custom callbacks
@dashboard.app.callback(...)
def custom_visualization():
    # Your code here
    pass

dashboard.run()
```

---

## 📦 Automated Inventory Recommendations

Smart inventory ordering with ML-powered recommendations.

### Safety Stock Calculation

```python
from src.recommendations.inventory import InventoryRecommendationEngine

recommender = InventoryRecommendationEngine(your_data)

# Calculate safety stock
safety = recommender.calculate_safety_stock(
    product='Coffee Beans',
    service_level=0.95,      # 95% service level
    lead_time_days=7         # 7-day supplier lead time
)

print(f"Safety Stock: {safety['safety_stock']}")
print(f"Reorder Point: {safety['reorder_point']}")
```

### Economic Order Quantity (EOQ)

```python
# Optimize order quantities
eoq = recommender.calculate_economic_order_quantity(
    product='Coffee Beans',
    order_cost=50,            # $50 per order
    holding_cost_pct=0.25,    # 25% annual holding cost
    unit_cost=15              # $15 per unit
)

print(f"Optimal Order: {eoq['economic_order_quantity']} units")
print(f"Order Every: {eoq['order_frequency_days']} days")
```

### Reorder Recommendations

```python
# Your current inventory
current_inventory = {
    'Coffee Beans': 50,
    'Espresso': 30,
    'Latte': 25
}

# Get recommendations
recommendations = recommender.generate_reorder_recommendations(
    current_inventory=current_inventory,
    lead_time_days=7,
    service_level=0.95
)

for rec in recommendations:
    if rec['urgency'] == 'CRITICAL':
        print(f"🚨 URGENT: Order {rec['product']}")
        print(f"   Recommended: {rec['recommended_order_qty']} units")
        print(f"   Days until stockout: {rec['estimated_days_until_stockout']}")
```

### Seasonal Ordering Plan

```python
# Plan for upcoming seasons
seasonal_plan = recommender.generate_seasonal_ordering_plan(
    months_ahead=3
)

print(seasonal_plan)
```

### Complete Recommendations

```python
# Get all recommendations at once
summary = recommender.get_recommendations_summary(current_inventory)

print(f"Products needing reorder: {summary['products_needing_reorder']}")
print(f"Critical items: {len(summary['critical_items'])}")

for item in summary['critical_items']:
    print(f"⚠️  {item['product']}: Order NOW!")
```

---

## 🎯 Best Practices

### Data Quality

- **Minimum requirements:**
  - 6+ months of historical data
  - 100+ transactions
  - Multiple products and customers

- **Optimal:**
  - 2+ years of data
  - Consistent daily data
  - Clean, de-duplicated records

### Model Selection

| Use Case | Recommended Model |
|----------|------------------|
| Short-term forecast (1-7 days) | XGBoost, Simple methods |
| Medium-term (1-3 months) | Prophet, LSTM |
| Long-term (3+ months) | Ensemble methods |
| Customer behavior | Random Forest, XGBoost |
| Inventory optimization | Statistical methods |

### Performance Optimization

```python
# For large datasets, process in chunks
chunk_size = 10000
for chunk in pd.read_csv('large_file.csv', chunksize=chunk_size):
    # Process chunk
    pass

# Use sampling for exploratory analysis
sample_data = data.sample(frac=0.1, random_state=42)
```

### Monitoring & Maintenance

- **Weekly:** Check forecast accuracy
- **Monthly:** Retrain models with new data
- **Quarterly:** Evaluate and tune hyperparameters
- **Ongoing:** Monitor data quality and anomalies

---

## 📚 Additional Resources

- [Square API Documentation](https://developer.squareup.com/docs)
- [TensorFlow/Keras Guides](https://www.tensorflow.org/tutorials)
- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [Plotly Dash Documentation](https://dash.plotly.com/)

---

## 🆘 Troubleshooting

### Import Errors

```bash
# TensorFlow not found
pip install tensorflow

# XGBoost not found
pip install xgboost

# Dash not found
pip install dash dash-bootstrap-components
```

### Memory Issues

```python
# Reduce LSTM model size
model = forecaster.build_lstm_model((30, 1))  # Smaller lookback

# Use fewer epochs
lstm_result = forecaster.train_lstm_forecast(epochs=20)  # Instead of 50

# Sample your data
sampled_data = data.sample(frac=0.5, random_state=42)
```

### Slow Performance

```python
# Use GPU for deep learning
# Install: pip install tensorflow-gpu

# Reduce data frequency
df_weekly = df.resample('W').sum()  # Weekly instead of daily

# Use simpler models for exploration
# XGBoost is faster than LSTM for most cases
```

---

For more examples, see the `examples/` directory!
