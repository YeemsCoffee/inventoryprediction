# Customer Trend Analysis & Inventory Prediction ML App

An intelligent machine learning application that analyzes customer trends and behaviors across years and seasons to help businesses make data-driven inventory and operational decisions.

## 🎯 Overview

This ML-powered application learns from historical customer transaction data to:

- **Identify Seasonal Patterns**: Understand how customer behavior changes across seasons
- **Analyze Yearly Trends**: Track long-term growth and customer retention
- **Segment Customers**: Automatically group customers based on behavior patterns
- **Forecast Demand**: Predict future inventory needs and customer activity
- **Generate Insights**: Provide actionable recommendations for business decisions

## ✨ Key Features

### 📊 Seasonal Trend Analysis
- Analyze customer behavior patterns across seasons (Spring, Summer, Fall, Winter)
- Identify peak seasons for specific products
- Detect seasonal anomalies and unusual patterns
- Monthly trend analysis with statistical insights

### 📈 Yearly Growth Analysis
- Year-over-year growth tracking
- Customer retention rate calculation
- Customer Lifetime Value (CLV) analysis
- Product trend analysis over time
- Simple predictive modeling for next year's metrics

### 👥 Customer Segmentation
- Automatic customer segmentation using K-Means clustering
- RFM (Recency, Frequency, Monetary) analysis
- Segment labeling (High Value, Loyal, At Risk, New Customers, etc.)
- Personalized recommendations for each segment

### 🔮 Demand Forecasting
- Time series forecasting for overall demand
- Product-level demand predictions
- Confidence intervals for forecasts
- Support for multiple time frequencies (daily, weekly, monthly)

### 📊 Visualization & Reporting
- Beautiful, publication-ready charts
- Seasonal trend visualizations
- Yearly growth plots
- Customer segment analysis charts
- Product seasonality heatmaps
- Forecast visualizations with confidence intervals

## 🚀 Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/YeemsCoffee/inventoryprediction.git
cd inventoryprediction
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install in development mode:
```bash
pip install -e .
```

### Basic Usage

#### Option 1: Run the Demo
```bash
python examples/demo.py
```

#### Option 2: Use with Your Own Data
```python
from src.app import CustomerTrendApp

# Initialize the app
app = CustomerTrendApp()

# Load your data
app.load_data_from_csv(
    filepath='your_data.csv',
    date_column='date',
    customer_column='customer_id',
    amount_column='quantity',
    product_column='product_name'
)

# Generate comprehensive analysis
report = app.generate_full_report(n_segments=4)

# Print summary
app.print_summary(report)
```

#### Option 3: Test with Sample Data
```python
from src.app import CustomerTrendApp

app = CustomerTrendApp()
app.create_sample_data(n_customers=150, n_transactions=8000)
report = app.generate_full_report()
```

## 📁 Project Structure

```
inventoryprediction/
├── src/
│   ├── app.py                    # Main application interface
│   ├── data/
│   │   └── customer_data.py      # Data processing and feature engineering
│   ├── analysis/
│   │   ├── seasonal_trends.py    # Seasonal analysis algorithms
│   │   └── yearly_trends.py      # Yearly trend analysis
│   ├── models/
│   │   ├── forecaster.py         # Time series forecasting models
│   │   └── segmentation.py       # Customer segmentation (K-Means)
│   └── visualization/
│       └── charts.py             # Visualization tools
├── data/
│   ├── raw/                      # Place your raw data here
│   ├── processed/                # Processed data will be saved here
│   └── sample/                   # Sample data for testing
├── examples/
│   ├── demo.py                   # Full demonstration script
│   └── load_csv_example.py       # Example loading CSV data
├── tests/                        # Unit tests
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
└── README.md                     # This file
```

## 📊 Data Format

Your CSV file should have the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `date` | Transaction date | 2024-01-15 |
| `customer_id` | Unique customer identifier | 1001 |
| `product` | Product name or category | Coffee Beans |
| `amount` | Quantity purchased | 2 |
| `price` | Price per item (optional) | 15.99 |

Example CSV:
```csv
date,customer_id,product,amount,price
2024-01-15,1,Coffee Beans,2,15.99
2024-01-16,2,Latte,1,4.50
2024-01-17,1,Espresso,3,3.00
```

## 🔧 Advanced Usage

### Individual Analysis Components

#### Seasonal Analysis
```python
from src.analysis.seasonal_trends import SeasonalTrendAnalyzer

analyzer = SeasonalTrendAnalyzer(your_data)
seasonal_patterns = analyzer.analyze_seasonal_patterns()
product_seasonality = analyzer.analyze_product_seasonality()
recommendations = analyzer.get_seasonal_recommendations()
```

#### Yearly Trends
```python
from src.analysis.yearly_trends import YearlyTrendAnalyzer

analyzer = YearlyTrendAnalyzer(your_data)
yearly_growth = analyzer.analyze_yearly_growth()
retention = analyzer.calculate_customer_retention()
predictions = analyzer.predict_next_year_metrics()
```

#### Customer Segmentation
```python
from src.models.segmentation import CustomerSegmentation

segmentation = CustomerSegmentation(your_data)
segmentation.perform_kmeans_segmentation(n_clusters=4)
segments = segmentation.analyze_segments()
labels = segmentation.label_segments()
recommendations = segmentation.get_segment_recommendations()
```

#### Demand Forecasting
```python
from src.models.forecaster import CustomerTrendForecaster

forecaster = CustomerTrendForecaster(your_data)
forecast = forecaster._simple_forecast(periods=30, date_column='date',
                                       value_column='amount', frequency='D')
```

### Creating Visualizations

```python
from src.visualization.charts import TrendVisualizer

viz = TrendVisualizer()

# Seasonal trends
viz.plot_seasonal_trends(seasonal_data, save_path='seasonal_trends.png')

# Yearly growth
viz.plot_yearly_growth(yearly_data, save_path='yearly_growth.png')

# Product seasonality heatmap
viz.plot_product_seasonality(product_season_data, save_path='product_heatmap.png')

# Customer segments
viz.plot_customer_segments(segment_stats, segment_labels, save_path='segments.png')
```

## 🎓 Use Cases

### Retail & E-commerce
- Optimize inventory levels based on seasonal demand
- Identify high-value customers for targeted marketing
- Predict stockout risks before they happen

### Coffee Shops & Restaurants
- Plan seasonal menu items based on customer preferences
- Optimize staff scheduling for peak seasons
- Identify loyal customers for loyalty programs

### Subscription Services
- Predict customer churn and retention
- Identify at-risk customers for re-engagement
- Forecast revenue and growth trends

## 🛠️ Technologies Used

- **Python 3.8+**: Core programming language
- **pandas & numpy**: Data manipulation and numerical computing
- **scikit-learn**: Machine learning (K-Means clustering, preprocessing)
- **Prophet** (optional): Advanced time series forecasting
- **statsmodels**: Statistical analysis
- **matplotlib & seaborn**: Data visualization
- **plotly**: Interactive visualizations

## 📈 Example Output

When you run the demo, you'll get insights like:

```
📋 ANALYSIS SUMMARY
============================================================

📊 DATA OVERVIEW:
  • Total Transactions: 8000
  • Unique Customers: 150
  • Unique Products: 8
  • Date Range: 2020-01-01 to 2024-12-31

🌱 SEASONAL INSIGHTS:
  • Stock up for Fall - highest customer activity season
  • Increase Coffee Beans inventory for Winter

📈 YEARLY TRENDS:
  • Customer Trend: Moderate Growth
  • Avg Customer Growth: 5.23%

👥 CUSTOMER SEGMENTS:
  • High Value: 25 customers (16.7%)
  • Loyal Customers: 38 customers (25.3%)
  • Regular Customers: 52 customers (34.7%)
  • At Risk: 35 customers (23.3%)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

## 🙏 Acknowledgments

Built with ❤️ for businesses that want to make data-driven decisions about inventory and customer engagement.
