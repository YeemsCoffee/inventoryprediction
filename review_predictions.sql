-- Review generated predictions

-- 1. Summary by product and location
SELECT
    product_name,
    location,
    COUNT(*) as forecast_days,
    MIN(forecast_date) as first_forecast,
    MAX(forecast_date) as last_forecast,
    ROUND(AVG(forecasted_quantity), 2) as avg_daily_quantity,
    ROUND(SUM(forecasted_quantity), 2) as total_30day_quantity
FROM predictions.demand_forecasts
GROUP BY product_name, location
ORDER BY location, total_30day_quantity DESC;

-- 2. Sample predictions for Vienna Latte (Whole milk) at Location 1
-- Showing first 7 days with day of week
SELECT
    forecast_date,
    TO_CHAR(forecast_date, 'Day') as day_of_week,
    ROUND(forecasted_quantity, 2) as predicted_quantity,
    model_type,
    trained_at
FROM predictions.demand_forecasts
WHERE product_name = 'Vienna Latte (Whole milk)'
  AND location = 'Location 1'
ORDER BY forecast_date
LIMIT 7;

-- 3. Compare predictions across locations for same product
SELECT
    product_name,
    location,
    forecast_date,
    ROUND(forecasted_quantity, 2) as quantity
FROM predictions.demand_forecasts
WHERE product_name IN ('Vienna Latte (Whole milk)', 'Americano')
  AND forecast_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 6
ORDER BY product_name, forecast_date, location;

-- 4. Weekly totals by product for material planning
SELECT
    product_name,
    location,
    ROUND(SUM(forecasted_quantity), 2) as week1_total,
    ROUND(AVG(forecasted_quantity), 2) as week1_daily_avg
FROM predictions.demand_forecasts
WHERE forecast_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 6
GROUP BY product_name, location
ORDER BY location, week1_total DESC;

-- 5. Total count of predictions
SELECT COUNT(*) as total_predictions FROM predictions.demand_forecasts;
