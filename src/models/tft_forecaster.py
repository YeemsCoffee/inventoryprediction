"""
Temporal Fusion Transformer (TFT) for demand forecasting using Darts.
Production implementation with per-(product, location) models and future covariates.
"""

from typing import Dict, Tuple, Optional

import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

# Placeholder for second store opening (adjust as needed)
SECOND_STORE_OPEN_DATE = pd.Timestamp("2023-06-01")


class TFTForecaster:
    """
    Temporal Fusion Transformer using Darts library.
    Handles per-(product, location) demand forecasting with future covariates:
    - Calendar features (day of week, month)
    - Weather features (temperature, precipitation)
    - Step change indicator for second store opening
    """

    def __init__(
        self,
        data: pd.DataFrame,
        date_col: str = "date",
        product_col: str = "product",
        target_col: str = "amount",
        location_col: str = "location",
        postal_code_col: str = "postal_code",
        weather_df: Optional[pd.DataFrame] = None,
        weather_date_col: str = "date",
        weather_postal_code_col: str = "postal_code",
    ):
        """
        Initialize TFT forecaster.

        Args:
            data: DataFrame with columns [date_col, product_col, location_col, postal_code_col, target_col]
            date_col: Name of the date column
            product_col: Name of the product identifier column
            target_col: Name of the demand/quantity column
            location_col: Name of the location column (for display)
            postal_code_col: Name of the postal code column (for joining weather)
            weather_df: Optional weather DataFrame with [date, postal_code, temp_max, temp_min, precipitation, ...]
            weather_date_col: Date column in weather_df
            weather_postal_code_col: Postal code column in weather_df (for joining)
        """
        self.data = data.copy()
        self.date_col = date_col
        self.product_col = product_col
        self.target_col = target_col
        self.location_col = location_col
        self.postal_code_col = postal_code_col
        self.weather_df = weather_df.copy() if weather_df is not None else None
        self.weather_date_col = weather_date_col
        self.weather_postal_code_col = weather_postal_code_col

        # Ensure dates are datetime
        self.data[self.date_col] = pd.to_datetime(self.data[self.date_col])
        if self.weather_df is not None:
            self.weather_df[self.weather_date_col] = pd.to_datetime(
                self.weather_df[self.weather_date_col]
            )

        # Store models, scalers, and series per (product, location)
        # Keys are "product|location" strings
        self.models: Dict[str, "TFTModel"] = {}
        self.target_scalers: Dict[str, "Scaler"] = {}
        self.covariate_scalers: Dict[str, "Scaler"] = {}
        self.series_unscaled: Dict[str, "TimeSeries"] = {}
        self.series_scaled: Dict[str, "TimeSeries"] = {}
        self.covariates: Dict[str, "TimeSeries"] = {}

    def _make_key(self, product_name: str, location: str) -> str:
        """Create a unique key for (product, location) pair."""
        return f"{product_name}|{location}"

    def _prepare_daily_series(
        self, product_name: str, location: str
    ) -> "TimeSeries":
        """
        Build a continuous daily TimeSeries for a single (product, location).

        Args:
            product_name: Product identifier
            location: Location name

        Returns:
            Darts TimeSeries with daily aggregated demand
        """
        from darts import TimeSeries

        # Filter for this product and location
        df_prod = self.data[
            (self.data[self.product_col] == product_name)
            & (self.data[self.location_col] == location)
        ].copy()

        if df_prod.empty:
            raise ValueError(
                f"No data found for product='{product_name}', location='{location}'"
            )

        # Aggregate by date (sum daily quantities)
        df_prod = (
            df_prod.groupby(self.date_col)[self.target_col]
            .sum()
            .reset_index()
            .sort_values(self.date_col)
        )

        # Build continuous daily date range
        full_dates = pd.date_range(
            start=df_prod[self.date_col].min(),
            end=df_prod[self.date_col].max(),
            freq="D",
        )

        df_full = (
            df_prod.set_index(self.date_col)
            .reindex(full_dates, fill_value=0)
            .reset_index()
        )
        df_full.columns = [self.date_col, self.target_col]

        # Create TimeSeries (unscaled)
        series = TimeSeries.from_dataframe(
            df_full,
            time_col=self.date_col,
            value_cols=self.target_col,
            freq="D",
        )
        return series

    def _prepare_covariates(
        self, product_name: str, location: str, postal_code: str, target_series: "TimeSeries"
    ) -> "TimeSeries":
        """
        Build future covariates TimeSeries for a (product, location).

        Includes:
        - Calendar features (day_of_week, month as one-hot)
        - Weather features (if available)
        - Step change indicator for second store opening

        Covariates are extended into the future to support validation and prediction.

        Args:
            product_name: Product identifier
            location: Location name
            target_series: The target TimeSeries (for date range alignment)

        Returns:
            Darts TimeSeries with future covariates
        """
        from darts import TimeSeries, concatenate
        from darts.utils.timeseries_generation import datetime_attribute_timeseries

        # Get date range from target series and extend into future
        start_date = target_series.start_time()
        end_date = target_series.end_time()

        # Extend covariates 365 days into the future to cover validation and predictions
        extended_end_date = end_date + pd.Timedelta(days=365)

        # Create extended date range
        extended_date_range = pd.date_range(start=start_date, end=extended_end_date, freq="D")

        # Create a dummy extended series for generating calendar features
        extended_series = TimeSeries.from_times_and_values(
            times=extended_date_range,
            values=np.zeros(len(extended_date_range))
        )

        # 1. Calendar covariates using datetime_attribute_timeseries
        # Day of week (0=Monday, 6=Sunday) - one-hot encoded
        dow_series = datetime_attribute_timeseries(
            extended_series,
            attribute="dayofweek",
            one_hot=True,
            cyclic=False,
        )

        # Month (1-12) - one-hot encoded
        month_series = datetime_attribute_timeseries(
            extended_series,
            attribute="month",
            one_hot=True,
            cyclic=False,
        )

        # 2. Step change indicator for second store opening
        # Create a binary series: 0 before SECOND_STORE_OPEN_DATE, 1 after
        step_change = (extended_date_range >= SECOND_STORE_OPEN_DATE).astype(int)
        step_df = pd.DataFrame(
            {"date": extended_date_range, "second_store_indicator": step_change}
        )
        step_series = TimeSeries.from_dataframe(
            step_df, time_col="date", value_cols="second_store_indicator", freq="D"
        )

        # 3. Weather covariates (if available)
        weather_series = None
        if self.weather_df is not None:
            # Filter weather for this location using postal code
            weather_loc = self.weather_df[
                self.weather_df[self.weather_postal_code_col] == postal_code
            ].copy()

            if not weather_loc.empty:
                # Identify numeric weather columns (exclude date and postal_code)
                exclude_cols = {self.weather_date_col, self.weather_postal_code_col}
                weather_cols = [
                    col
                    for col in weather_loc.columns
                    if col not in exclude_cols
                    and pd.api.types.is_numeric_dtype(weather_loc[col])
                ]

                if weather_cols:
                    # Sort by date
                    weather_loc = weather_loc.sort_values(
                        self.weather_date_col
                    ).reset_index(drop=True)

                    # Create weather TimeSeries
                    weather_series = TimeSeries.from_dataframe(
                        weather_loc,
                        time_col=self.weather_date_col,
                        value_cols=weather_cols,
                        freq="D",
                        fill_missing_dates=True,
                        fillna_value=0,
                    )

                    # Extend weather to cover the extended date range
                    # For dates beyond available weather, use forward fill (last known values)
                    weather_end = weather_series.end_time()
                    if extended_end_date > weather_end:
                        # Get last values using universal API
                        last_values = weather_series[-1:].values()[0]  # Last row of values

                        # Create extended date range
                        n_days_to_extend = int((extended_end_date - weather_end).days)
                        extended_dates = pd.date_range(
                            start=weather_end + pd.Timedelta(days=1),
                            end=extended_end_date,
                            freq="D"
                        )

                        # Create DataFrame with forward-filled values
                        extended_df = pd.DataFrame(
                            [last_values] * len(extended_dates),
                            index=extended_dates,
                            columns=weather_cols
                        )
                        extended_df.index.name = 'date'

                        # Create TimeSeries from extended data
                        extended_series = TimeSeries.from_dataframe(
                            extended_df.reset_index(),
                            time_col="date",
                            value_cols=weather_cols,
                            freq="D"
                        )

                        # Append to original weather series
                        from darts import concatenate as concat_series
                        weather_series = concat_series([weather_series, extended_series], axis=0)

        # Combine all covariates
        covariate_list = [dow_series, month_series, step_series]
        if weather_series is not None:
            covariate_list.append(weather_series)

        # Stack covariates into a single multivariate TimeSeries
        combined_covariates = concatenate(covariate_list, axis=1)

        return combined_covariates

    def prepare_data_for_product(
        self,
        product_name: str,
        location: str,
        val_ratio: float = 0.2,
    ) -> Tuple["TimeSeries", "TimeSeries", "TimeSeries", "TimeSeries"]:
        """
        Prepare scaled train/val series and covariates for a (product, location).

        Args:
            product_name: Product to forecast
            location: Location name
            val_ratio: Fraction of data to use for validation (e.g. 0.2 = 20%)

        Returns:
            (train_scaled, val_scaled, train_covs, val_covs)
        """
        from darts.dataprocessing.transformers import Scaler

        key = self._make_key(product_name, location)

        # Get postal code for this location
        location_data = self.data[self.data[self.location_col] == location]
        if location_data.empty:
            raise ValueError(f"No data found for location: {location}")
        postal_code = location_data[self.postal_code_col].iloc[0]

        # Build unscaled target TimeSeries
        series = self._prepare_daily_series(product_name, location)

        # Scale target using Darts Scaler (fit once on full history)
        target_scaler = Scaler()
        series_scaled = target_scaler.fit_transform(series)

        # Build covariates
        covariates = self._prepare_covariates(product_name, location, postal_code, series)

        # Optionally scale covariates (usually not needed if bounded)
        # For simplicity, we'll leave covariates unscaled here
        # If you want to scale them, create a separate Scaler for covariates

        # Store for later use
        self.target_scalers[key] = target_scaler
        self.series_unscaled[key] = series
        self.series_scaled[key] = series_scaled
        self.covariates[key] = covariates

        # Train/val split
        n_total = len(series_scaled)
        if n_total < 10:
            raise ValueError(
                f"Not enough data points ({n_total}) for product='{product_name}', location='{location}'"
            )

        n_val = max(1, int(n_total * val_ratio))
        n_train = n_total - n_val

        train = series_scaled[:n_train]
        val = series_scaled[n_train:]

        # Split covariates with the same indices
        train_covs = covariates[:n_train]
        val_covs = covariates[n_train:]

        return train, val, train_covs, val_covs

    def train_tft(
        self,
        product_name: str,
        location: str,
        forecast_horizon: int = 7,
        input_chunk_length: int = 30,
        hidden_size: int = 32,
        num_attention_heads: int = 4,
        dropout: float = 0.1,
        n_epochs: int = 50,
    ) -> Dict:
        """
        Train TFT model for a single (product, location).

        Args:
            product_name: Product to train model for
            location: Location name
            forecast_horizon: Days to forecast
            input_chunk_length: Historical window size
            hidden_size: Hidden layer size
            num_attention_heads: Number of attention heads
            dropout: Dropout rate
            n_epochs: Training epochs

        Returns:
            Dict with training results (product, location, MAE, RMSE, etc.)
        """
        from darts.models import TFTModel
        from darts.metrics import mae, rmse
        from pytorch_lightning.callbacks import EarlyStopping

        key = self._make_key(product_name, location)

        print("=" * 70)
        print(f"🚀 TRAINING TFT FOR: {product_name} @ {location}")
        print("=" * 70)

        # Prepare scaled train/val series and covariates
        train, val, train_covs, val_covs = self.prepare_data_for_product(
            product_name, location
        )
        series_scaled_full = self.series_scaled[key]
        series_unscaled_full = self.series_unscaled[key]
        target_scaler = self.target_scalers[key]
        covariates_full = self.covariates[key]

        print(f"📊 Total points:   {len(series_scaled_full)}")
        print(f"📊 Train points:   {len(train)}")
        print(f"📊 Validation pts: {len(val)}")
        print(f"🌤️  Covariate features: {covariates_full.n_components}")

        # Initialize TFT model
        model = TFTModel(
            input_chunk_length=input_chunk_length,
            output_chunk_length=forecast_horizon,
            hidden_size=hidden_size,
            lstm_layers=2,
            num_attention_heads=num_attention_heads,
            dropout=dropout,
            batch_size=16,
            n_epochs=n_epochs,
            optimizer_kwargs={"lr": 1e-3},
            add_relative_index=True,
            random_state=42,
            pl_trainer_kwargs={
                "accelerator": "auto",
                "callbacks": [
                    EarlyStopping(
                        monitor="val_loss",
                        patience=5,
                        min_delta=1e-4,
                        mode="min",
                    )
                ],
            },
            save_checkpoints=True,
            force_reset=True,
        )

        # Train with covariates
        print("\n🎯 Starting training...")
        model.fit(
            series=train,
            future_covariates=train_covs,
            val_series=val,
            val_future_covariates=val_covs,
            verbose=True,
        )

        # Store model
        self.models[key] = model

        # ---------- Validation forecast ----------
        # Forecast the validation period from the end of training data
        n_val = len(val)

        # Slice covariates to cover ONLY train + validation period
        # This ensures predicted timestamps align exactly with validation timestamps
        covs_for_val = train_covs.append(val_covs)

        pred_scaled = model.predict(
            n=n_val,
            series=train,  # Predict from end of training, not full series
            future_covariates=covs_for_val,  # Use only train+val covariates
        )

        # Inverse-transform predictions and true validation slice
        pred_unscaled = target_scaler.inverse_transform(pred_scaled)

        # Get the actual validation data (unscaled)
        n_total = len(series_scaled_full)
        val_unscaled = series_unscaled_full[n_total - n_val :]

        # Ensure timestamps align exactly
        if not pred_unscaled.time_index.equals(val_unscaled.time_index):
            raise ValueError(
                f"Validation prediction timestamps do not match validation data!\n"
                f"Predicted: {pred_unscaled.time_index[0]} to {pred_unscaled.time_index[-1]}\n"
                f"Expected:  {val_unscaled.time_index[0]} to {val_unscaled.time_index[-1]}"
            )

        # Compute metrics
        mae_val = mae(val_unscaled, pred_unscaled)
        rmse_val = rmse(val_unscaled, pred_unscaled)

        print(f"\n✅ Training complete for {product_name} @ {location}!")
        print(f"📊 Validation MAE:  {mae_val:.3f}")
        print(f"📊 Validation RMSE: {rmse_val:.3f}")
        print("=" * 70)

        return {
            "product": product_name,
            "location": location,
            "mae": mae_val,
            "rmse": rmse_val,
            "model": model,
            "train_size": len(train),
            "val_size": len(val),
        }

    def predict(
        self,
        product_name: str,
        location: str,
        n_days: int = 7,
    ) -> pd.DataFrame:
        """
        Generate forward predictions for a (product, location).

        Args:
            product_name: Product to predict
            location: Location name
            n_days: Number of days to forecast

        Returns:
            DataFrame with columns: [forecast_date, forecasted_quantity, product_name, location]
        """
        key = self._make_key(product_name, location)

        if key not in self.models:
            raise ValueError(
                f"No trained model found for product='{product_name}', location='{location}'"
            )

        model = self.models[key]
        target_scaler = self.target_scalers[key]
        series_scaled_full = self.series_scaled[key]
        series_unscaled_full = self.series_unscaled[key]
        covariates_full = self.covariates[key]

        # Check if covariates extend far enough into the future
        # (Assuming covariates are already prepared to cover the forecast horizon)
        # If weather data is not available for future dates, this may fail
        # In that case, you'd need to extend the covariate series with forecast weather

        # Forecast future n_days from the end of the series
        pred_scaled = model.predict(
            n=n_days,
            series=series_scaled_full,
            future_covariates=covariates_full,
        )

        # Inverse transform to original scale
        pred_unscaled = target_scaler.inverse_transform(pred_scaled)

        # Convert to pandas using universal approach (works across all darts versions)
        df_forecast = pd.DataFrame(
            {
                "forecast_date": pred_unscaled.time_index,
                "forecasted_quantity": pred_unscaled.values().flatten(),
                "product_name": product_name,
                "location": location,
            }
        )

        # Sanity check: last observed value vs first forecast
        last_actual = series_unscaled_full[-1:].values()[0][0]
        first_pred = pred_unscaled[0].values()[0][0]
        print(
            f"🔎 {product_name} @ {location} — last actual: {last_actual:.2f}, "
            f"first forecast: {first_pred:.2f}"
        )

        return df_forecast
