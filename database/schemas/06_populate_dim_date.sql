-- ============================================================================
-- Populate Date Dimension
-- Generates dates from 2020-01-01 to 2030-12-31
-- ============================================================================

INSERT INTO gold.dim_date (
    date_key,
    date,
    year,
    quarter,
    month,
    month_name,
    week_of_year,
    day_of_month,
    day_of_week,
    day_name,
    is_weekend,
    season
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER AS date_key,
    d AS date,
    EXTRACT(YEAR FROM d)::INTEGER AS year,
    EXTRACT(QUARTER FROM d)::INTEGER AS quarter,
    EXTRACT(MONTH FROM d)::INTEGER AS month,
    TO_CHAR(d, 'Month') AS month_name,
    EXTRACT(WEEK FROM d)::INTEGER AS week_of_year,
    EXTRACT(DAY FROM d)::INTEGER AS day_of_month,
    EXTRACT(DOW FROM d)::INTEGER AS day_of_week,
    TO_CHAR(d, 'Day') AS day_name,
    CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,
    CASE
        WHEN EXTRACT(MONTH FROM d) IN (12, 1, 2) THEN 'Winter'
        WHEN EXTRACT(MONTH FROM d) IN (3, 4, 5) THEN 'Spring'
        WHEN EXTRACT(MONTH FROM d) IN (6, 7, 8) THEN 'Summer'
        WHEN EXTRACT(MONTH FROM d) IN (9, 10, 11) THEN 'Fall'
    END AS season
FROM generate_series('2020-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) AS d
ON CONFLICT (date_key) DO NOTHING;

-- Add common US holidays (customize for your business)
UPDATE gold.dim_date
SET is_holiday = TRUE, holiday_name = 'New Year''s Day'
WHERE month = 1 AND day_of_month = 1;

UPDATE gold.dim_date
SET is_holiday = TRUE, holiday_name = 'Independence Day'
WHERE month = 7 AND day_of_month = 4;

UPDATE gold.dim_date
SET is_holiday = TRUE, holiday_name = 'Christmas Day'
WHERE month = 12 AND day_of_month = 25;

UPDATE gold.dim_date
SET is_holiday = TRUE, holiday_name = 'Thanksgiving'
WHERE date IN (
    -- Thanksgiving is 4th Thursday of November
    SELECT d
    FROM generate_series('2020-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) AS d
    WHERE EXTRACT(MONTH FROM d) = 11
      AND EXTRACT(DOW FROM d) = 4
      AND EXTRACT(DAY FROM d) BETWEEN 22 AND 28
);

UPDATE gold.dim_date
SET is_holiday = TRUE, holiday_name = 'Black Friday'
WHERE date IN (
    -- Black Friday is day after Thanksgiving
    SELECT d + INTERVAL '1 day'
    FROM generate_series('2020-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) AS d
    WHERE EXTRACT(MONTH FROM d) = 11
      AND EXTRACT(DOW FROM d) = 4
      AND EXTRACT(DAY FROM d) BETWEEN 22 AND 28
);

COMMENT ON TABLE gold.dim_date IS 'Date dimension populated from 2020 to 2030';
