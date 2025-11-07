# Usage Guide - Customer Trend Analysis ML App

This guide provides detailed instructions on how to use the Customer Trend Analysis ML App effectively.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Loading Your Data](#loading-your-data)
3. [Running Analyses](#running-analyses)
4. [Understanding the Results](#understanding-the-results)
5. [Creating Visualizations](#creating-visualizations)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

```bash
# Install all required packages
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## Loading Your Data

### Method 1: Load from CSV

Prepare your CSV file with the following columns:
- `date`: Transaction date (format: YYYY-MM-DD)
- `customer_id`: Unique customer identifier
- `product`: Product name or category
- `amount`: Quantity purchased
- `price`: Price (optional)

```python
from src.app import CustomerTrendApp

app = CustomerTrendApp()
app.load_data_from_csv(
    filepath='data/raw/transactions.csv',
    date_column='transaction_date',
    customer_column='customer_id',
    amount_column='quantity',
    product_column='product_name'
)
```

### Method 2: Use Sample Data

Perfect for testing and learning:

```python
app = CustomerTrendApp()
app.create_sample_data(
    n_customers=150,
    n_transactions=8000,
    start_date='2020-01-01',
    end_date='2024-12-31'
)
```

## Running Analyses

### Complete Analysis (Recommended)

Generate a full report with all analyses:

```python
report = app.generate_full_report(n_segments=4)
app.print_summary(report)
```

### Individual Analyses

#### Seasonal Trends

```python
seasonal_results = app.analyze_seasonal_trends()

# Access different components
seasonal_patterns = seasonal_results['seasonal_patterns']
product_seasonality = seasonal_results['product_seasonality']
seasonal_peaks = seasonal_results['seasonal_peaks']
recommendations = seasonal_results['recommendations']
```

#### Yearly Trends

```python
yearly_results = app.analyze_yearly_trends()

# Access components
yearly_growth = yearly_results['yearly_growth']
retention = yearly_results['customer_retention']
clv = yearly_results['customer_lifetime_value']
predictions = yearly_results['predictions']
```

#### Customer Segmentation

```python
segmentation = app.segment_customers(n_segments=4)

# Access components
customer_features = segmentation['customer_features']
segment_analysis = segmentation['segment_analysis']
segment_labels = segmentation['segment_labels']
recommendations = segmentation['recommendations']
```

#### Demand Forecasting

```python
forecast = app.forecast_demand(periods=60, frequency='W')

# Access forecasts
overall_forecast = forecast['overall_forecast']
product_forecasts = forecast['product_forecasts']
```

## Understanding the Results

### Seasonal Analysis Results

**Seasonal Patterns DataFrame:**
- `season`: Season name
- `unique_customers`: Number of unique customers
- `total_items`: Total items sold
- `transaction_count`: Total transactions
- `pct_of_annual`: Percentage of annual activity

**Product Seasonality:**
- Shows which products are popular in which seasons
- `seasonal_index`: 100 = average, >100 = above average, <100 = below average

### Yearly Analysis Results

**Yearly Growth DataFrame:**
- `year`: Year
- `unique_customers`: Number of customers that year
- `customer_growth`: Year-over-year customer growth (%)
- `revenue_growth`: Year-over-year revenue growth (%)

**Customer Retention:**
- `retention_rate`: Percentage of customers who returned next year
- `new_customers`: Number of new customers gained

**Predictions:**
- `predicted_customers`: Expected customers next year
- `predicted_transactions`: Expected transactions next year
- `confidence`: Prediction confidence level (Low/Medium/High)

### Customer Segmentation Results

**Segment Labels:**
- **High Value**: Frequent buyers with high spend
- **Loyal Customers**: Regular, consistent purchasers
- **Regular Customers**: Average buying behavior
- **At Risk**: Haven't purchased recently
- **New Customers**: Recently acquired, low transaction count

**Segment Analysis DataFrame:**
- Shows average metrics for each segment
- Use to understand segment characteristics

### Forecast Results

**Forecast DataFrame:**
- `ds`: Date
- `yhat`: Predicted value
- `yhat_lower`: Lower confidence bound
- `yhat_upper`: Upper confidence bound

## Creating Visualizations

### Basic Visualization

```python
# After generating report
app.visualize_results(
    seasonal_data=report['seasonal_analysis']['seasonal_patterns'],
    yearly_data=report['yearly_analysis']['yearly_growth'],
    product_season_data=report['seasonal_analysis']['product_seasonality'],
    segment_data=report['customer_segmentation']
)
```

### Save Visualizations

```python
app.visualize_results(
    seasonal_data=report['seasonal_analysis']['seasonal_patterns'],
    yearly_data=report['yearly_analysis']['yearly_growth'],
    save_path='outputs/analysis'  # Will create analysis_seasonal.png, etc.
)
```

### Custom Visualizations

```python
from src.visualization.charts import TrendVisualizer

viz = TrendVisualizer()

# Create individual plots
viz.plot_seasonal_trends(seasonal_data, save_path='seasonal.png')
viz.plot_yearly_growth(yearly_data, save_path='yearly.png')
viz.plot_customer_segments(segment_stats, segment_labels, save_path='segments.png')
```

## Best Practices

### Data Quality

1. **Minimum Data Requirements:**
   - At least 6 months of historical data
   - At least 100 transactions
   - Multiple products for meaningful seasonality analysis

2. **Data Preparation:**
   - Remove duplicate transactions
   - Handle missing values appropriately
   - Ensure date formats are consistent
   - Remove test/internal transactions

3. **Date Ranges:**
   - For seasonal analysis: Need at least 1 full year
   - For yearly trends: Need at least 2 years
   - More data = better predictions

### Analysis Tips

1. **Customer Segmentation:**
   - Start with 4 segments
   - Increase to 5-6 if you have >500 customers
   - Review segment labels and adjust strategy accordingly

2. **Forecasting:**
   - Use weekly (`'W'`) frequency for short-term planning
   - Use monthly (`'M'`) for long-term strategy
   - Always check confidence intervals

3. **Seasonal Patterns:**
   - Compare multiple years to validate patterns
   - Account for special events/holidays
   - Consider external factors (weather, economy)

### Performance Optimization

```python
# For large datasets (>100K transactions)
# Process in chunks or aggregate first

# Example: Aggregate by day first
daily_data = data.groupby(['date', 'product']).agg({
    'customer_id': 'nunique',
    'amount': 'sum'
}).reset_index()
```

## Troubleshooting

### Common Issues

#### Issue: "No data loaded" error
**Solution:** Make sure to call `load_data_from_csv()` or `create_sample_data()` first

#### Issue: Insufficient data warnings
**Solution:** Ensure you have:
- At least 6 months of data
- At least 10 transactions per product
- Multiple customers

#### Issue: Visualizations not showing
**Solution:**
- In Jupyter notebooks, use `%matplotlib inline`
- In scripts, add `plt.show()` after creating visualizations
- Or save plots to files using `save_path` parameter

#### Issue: Memory errors with large datasets
**Solution:**
- Aggregate data before analysis
- Process products separately
- Use sampling for exploratory analysis

### Getting Help

If you encounter issues:

1. Check the error message carefully
2. Review the data format requirements
3. Try with sample data first to isolate the issue
4. Check GitHub issues for similar problems
5. Open a new issue with:
   - Error message
   - Code snippet
   - Data format (without sensitive info)

## Example Workflow

Here's a complete workflow from start to finish:

```python
from src.app import CustomerTrendApp

# 1. Initialize and load data
app = CustomerTrendApp()
app.load_data_from_csv('data/raw/sales.csv')

# 2. Generate comprehensive report
report = app.generate_full_report(n_segments=4)

# 3. Review summary
app.print_summary(report)

# 4. Create visualizations
app.visualize_results(
    seasonal_data=report['seasonal_analysis']['seasonal_patterns'],
    yearly_data=report['yearly_analysis']['yearly_growth'],
    product_season_data=report['seasonal_analysis']['product_seasonality'],
    segment_data=report['customer_segmentation'],
    save_path='outputs/analysis'
)

# 5. Extract specific insights
print("\nTop 3 Products by Season:")
product_peaks = report['seasonal_analysis']['seasonal_peaks']
for product, metrics in list(product_peaks.items())[:3]:
    print(f"  {product}: Peak in {metrics['peak_season']}")

print("\nCustomer Segment Recommendations:")
for rec in report['customer_segmentation']['recommendations']:
    print(f"  {rec['segment_label']}: {rec['recommendation']}")

# 6. Save results for later use
import pandas as pd
report['seasonal_analysis']['seasonal_patterns'].to_csv('outputs/seasonal_patterns.csv')
report['yearly_analysis']['yearly_growth'].to_csv('outputs/yearly_growth.csv')
```

## Next Steps

- Review the main [README.md](README.md) for more examples
- Check out [examples/demo.py](examples/demo.py) for a complete demonstration
- Explore individual modules in `src/` for advanced usage
- Customize the analysis for your specific business needs

---

For more information, visit the [GitHub repository](https://github.com/YeemsCoffee/inventoryprediction).
