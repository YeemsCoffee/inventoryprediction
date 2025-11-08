"""
Time series forecasting models for customer behavior and inventory prediction.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import warnings
warnings.filterwarnings('ignore')


class CustomerTrendForecaster:
    """Forecast customer trends and inventory needs using time series analysis."""

    def __init__(self, data: pd.DataFrame):
        """
        Initialize forecaster with historical data.

        Args:
            data: DataFrame with date and metric columns
        """
        self.data = data.copy()
        self.model = None
        self.forecast = None

    def prepare_time_series(self, date_column: str = 'date',
                           value_column: str = 'amount',
                           aggregation: str = 'sum',
                           frequency: str = 'D') -> pd.DataFrame:
        """
        Prepare time series data for forecasting.

        Args:
            date_column: Name of date column
            value_column: Name of value column to forecast
            aggregation: Aggregation method ('sum', 'mean', 'count')
            frequency: Time frequency ('D', 'W', 'M')

        Returns:
            Prepared time series DataFrame
        """
        df = self.data.copy()
        df[date_column] = pd.to_datetime(df[date_column])
        df = df.set_index(date_column)

        # Aggregate by frequency
        if aggregation == 'sum':
            ts = df[value_column].resample(frequency).sum()
        elif aggregation == 'mean':
            ts = df[value_column].resample(frequency).mean()
        elif aggregation == 'count':
            ts = df[value_column].resample(frequency).count()
        else:
            raise ValueError(f"Unknown aggregation: {aggregation}")

        return ts.reset_index()

    def forecast_prophet(self, periods: int = 30,
                        date_column: str = 'date',
                        value_column: str = 'amount',
                        frequency: str = 'D') -> pd.DataFrame:
        """
        Forecast using Facebook Prophet (if available).

        Args:
            periods: Number of periods to forecast
            date_column: Name of date column
            value_column: Name of value column
            frequency: Forecast frequency

        Returns:
            DataFrame with forecast
        """
        try:
            from prophet import Prophet

            # Prepare data in Prophet format
            ts = self.prepare_time_series(date_column, value_column, 'sum', frequency)
            ts.columns = ['ds', 'y']

            # Initialize and fit model
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=False,
                changepoint_prior_scale=0.05
            )

            model.fit(ts)
            self.model = model

            # Make future dataframe and forecast
            future = model.make_future_dataframe(periods=periods, freq=frequency)
            forecast = model.predict(future)

            self.forecast = forecast
            return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

        except ImportError:
            return self._simple_forecast(periods, date_column, value_column, frequency)

    def _simple_forecast(self, periods: int,
                        date_column: str,
                        value_column: str,
                        frequency: str) -> pd.DataFrame:
        """
        Simple moving average forecast as fallback.

        Args:
            periods: Number of periods to forecast
            date_column: Name of date column
            value_column: Name of value column
            frequency: Forecast frequency

        Returns:
            DataFrame with simple forecast
        """
        ts = self.prepare_time_series(date_column, value_column, 'sum', frequency)

        # Calculate moving average and trend
        window = min(7, len(ts) // 3)
        ts['ma'] = ts[value_column].rolling(window=window).mean()

        # Simple linear trend
        X = np.arange(len(ts)).reshape(-1, 1)
        y = ts[value_column].values

        # Calculate trend using least squares
        coeffs = np.polyfit(X.flatten(), y, 1)

        # Generate future dates
        last_date = ts[date_column].max()
        future_dates = pd.date_range(start=last_date, periods=periods + 1, freq=frequency)[1:]

        # Forecast using trend
        future_X = np.arange(len(ts), len(ts) + periods)
        forecast_values = coeffs[0] * future_X + coeffs[1]

        # Create forecast dataframe
        forecast_df = pd.DataFrame({
            'ds': future_dates,
            'yhat': forecast_values,
            'yhat_lower': forecast_values * 0.8,
            'yhat_upper': forecast_values * 1.2
        })

        return forecast_df

    def forecast_demand_by_product(self, periods: int = 30,
                                   product_column: str = 'product',
                                   frequency: str = 'W') -> Dict[str, pd.DataFrame]:
        """
        Forecast demand for each product separately.

        Args:
            periods: Number of periods to forecast
            product_column: Name of product column
            frequency: Forecast frequency

        Returns:
            Dictionary mapping products to their forecasts
        """
        forecasts = {}

        products = self.data[product_column].unique()

        for product in products:
            product_data = self.data[self.data[product_column] == product].copy()

            if len(product_data) < 10:  # Skip if insufficient data
                continue

            forecaster = CustomerTrendForecaster(product_data)
            try:
                forecast = forecaster._simple_forecast(periods, 'date', 'amount', frequency)
                forecasts[product] = forecast
            except Exception as e:
                print(f"Warning: Could not forecast for {product}: {str(e)}")
                continue

        return forecasts

    def calculate_forecast_accuracy(self, test_data: pd.DataFrame,
                                   forecast_data: pd.DataFrame) -> Dict:
        """
        Calculate forecast accuracy metrics.

        Args:
            test_data: Actual test data
            forecast_data: Forecast data

        Returns:
            Dictionary with accuracy metrics
        """
        # Align dates
        test_data = test_data.copy()
        forecast_data = forecast_data.copy()

        merged = test_data.merge(forecast_data, left_on='date', right_on='ds', how='inner')

        if len(merged) == 0:
            return {'error': 'No overlapping dates for accuracy calculation'}

        actual = merged.iloc[:, 1].values  # Actual values
        predicted = merged['yhat'].values

        # Calculate metrics
        mae = np.mean(np.abs(actual - predicted))
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))

        return {
            'mae': round(mae, 2),
            'mape': round(mape, 2),
            'rmse': round(rmse, 2),
            'samples': len(merged)
        }

    def get_forecast_summary(self) -> Dict:
        """
        Get summary statistics from the forecast.

        Returns:
            Dictionary with forecast summary
        """
        if self.forecast is None:
            return {'error': 'No forecast available. Run forecast_prophet first.'}

        forecast_values = self.forecast['yhat'].values
        lower_bound = self.forecast['yhat_lower'].values
        upper_bound = self.forecast['yhat_upper'].values

        return {
            'mean_forecast': round(np.mean(forecast_values), 2),
            'median_forecast': round(np.median(forecast_values), 2),
            'min_forecast': round(np.min(forecast_values), 2),
            'max_forecast': round(np.max(forecast_values), 2),
            'avg_lower_bound': round(np.mean(lower_bound), 2),
            'avg_upper_bound': round(np.mean(upper_bound), 2),
            'periods': len(forecast_values)
        }
