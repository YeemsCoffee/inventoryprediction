-- Check date range of actual sales data
SELECT
    MIN(d.date) as earliest_date,
    MAX(d.date) as latest_date,
    COUNT(DISTINCT d.date) as total_days,
    COUNT(*) as total_records
FROM gold.fact_sales f
JOIN gold.dim_date d ON f.date_key = d.date_key;

-- Check date range of predictions
SELECT
    MIN(forecast_date) as earliest_forecast,
    MAX(forecast_date) as latest_forecast,
    COUNT(DISTINCT forecast_date) as total_days,
    COUNT(*) as total_predictions
FROM predictions.demand_forecasts;

-- Check for overlap between predictions and actuals
SELECT
    COUNT(*) as overlapping_days
FROM (
    SELECT DISTINCT d.date
    FROM gold.fact_sales f
    JOIN gold.dim_date d ON f.date_key = d.date_key
) actuals
INNER JOIN (
    SELECT DISTINCT forecast_date as date
    FROM predictions.demand_forecasts
) predictions ON actuals.date = predictions.date;
