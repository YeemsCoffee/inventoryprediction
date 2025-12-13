"""
Temporal Fusion Transformer (TFT) for demand forecasting using Darts.
Clean, production-friendly implementation with per-product models.
"""

from typing import Dict, Tuple

import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")


class TFTForecaster:
    """
    Temporal Fusion Transformer using Darts library.
    Handles per-product demand forecasting with train/val split and metrics.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        date_col: str = "date",
        product_col: str = "product",
        target_col: str = "amount",
    ):
        """
        Initialize TFT forecaster.

        Args:
            data: DataFrame with at least [date_col, product_col, target_col]
            date_col: Name of the date column
            product_col: Name of the product identifier column
            target_col: Name of the demand/quantity column
        """
        self.data = data.copy()
        self.date_col = date_col
        self.product_col = product_col
        self.target_col = target_col

        # Ensure dates are datetime
        self.data[self.date_col] = pd.to_datetime(self.data[self.date_col])

        # Store models, scalers, and series per product
        self.models: Dict[str, "TFTModel"] = {}
        self.scalers: Dict[str, "Scaler"] = {}
        self.series_unscaled: Dict[str, "TimeSeries"] = {}
        self.series_scaled: Dict[str, "TimeSeries"] = {}

    def _prepare_daily_series(self, product_name: str) -> "TimeSeries":
        """
        Build a continuous daily TimeSeries for a single product.

        Args:
            product_name: Product identifier

        Returns:
            Darts TimeSeries with daily aggregated demand
        """
        from darts import TimeSeries

        # Filter for this product
        df_prod = self.data[self.data[self.product_col] == product_name].copy()
        if df_prod.empty:
            raise ValueError(f"No data found for product: {product_name}")

        # Aggregate by date (sum daily quantities)
        df_prod = (
            df_prod
            .groupby(self.date_col)[self.target_col]
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

    def prepare_data_for_product(
        self,
        product_name: str,
        val_ratio: float = 0.2,
    ) -> Tuple["TimeSeries", "TimeSeries"]:
        """
        Prepare scaled train/val series for a single product.

        Args:
            product_name: Product to forecast
            val_ratio: Fraction of data to use for validation (e.g. 0.2 = 20%)

        Returns:
            (train_scaled, val_scaled)
        """
        from darts.dataprocessing.transformers import Scaler

        # Build unscaled TimeSeries
        series = self._prepare_daily_series(product_name)

        # Scale using Darts Scaler (fit once on full history)
        scaler = Scaler()
        series_scaled = scaler.fit_transform(series)

        # Store for later use
        self.scalers[product_name] = scaler
        self.series_unscaled[product_name] = series
        self.series_scaled[product_name] = series_scaled

        # Train/val split
        n_total = len(series_scaled)
        if n_total < 10:
            raise ValueError(
                f"Not enough data points ({n_total}) for product {product_name}"
            )

        n_val = max(1, int(n_total * val_ratio))
        n_train = n_total - n_val

        train = series_scaled[:n_train]
        val = series_scaled[n_train:]

        return train, val

    def train_tft(
        self,
        product_name: str,
        forecast_horizon: int = 7,
        input_chunk_length: int = 30,
        hidden_size: int = 32,
        num_attention_heads: int = 4,
        dropout: float = 0.1,
        n_epochs: int = 50,
    ) -> Dict:
        """
        Train TFT model for a single product.

        Args:
            product_name: Product to train model for
            forecast_horizon: Days to forecast
            input_chunk_length: Historical window size
            hidden_size: Hidden layer size
            num_attention_heads: Number of attention heads
            dropout: Dropout rate
            n_epochs: Training epochs

        Returns:
            Dict with training results (MAE, RMSE, etc.)
        """
        from darts.models import TFTModel
        from darts.metrics import mae, rmse
        from pytorch_lightning.callbacks import EarlyStopping

        print("=" * 70)
        print(f"🚀 TRAINING TFT FOR PRODUCT: {product_name}")
        print("=" * 70)

        # Prepare scaled train/val series
        train, val = self.prepare_data_for_product(product_name)
        series_scaled_full = self.series_scaled[product_name]
        series_unscaled_full = self.series_unscaled[product_name]
        scaler = self.scalers[product_name]

        print(f"📊 Total points:   {len(series_scaled_full)}")
        print(f"📊 Train points:   {len(train)}")
        print(f"📊 Validation pts: {len(val)}")

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
            add_relative_index=True,  # simple time index covariate
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

        # Train
        print("\n🎯 Starting training...")
        model.fit(
            series=train,
            val_series=val,
            verbose=True,
        )

        # Store model
        self.models[product_name] = model

        # ---------- Validation forecast ----------
        # Forecast the next len(val) points from the end of the full series
        n_val = len(val)
        pred_scaled = model.predict(
            n=n_val,
            series=series_scaled_full,
        )

        # Inverse-transform predictions and true validation slice
        pred_unscaled = scaler.inverse_transform(pred_scaled)

        n_total = len(series_scaled_full)
        val_unscaled = series_unscaled_full[n_total - n_val :]

        # Compute metrics
        mae_val = mae(val_unscaled, pred_unscaled)
        rmse_val = rmse(val_unscaled, pred_unscaled)

        print(f"\n✅ Training complete for {product_name}!")
        print(f"📊 Validation MAE:  {mae_val:.3f}")
        print(f"📊 Validation RMSE: {rmse_val:.3f}")
        print("=" * 70)

        return {
            "product": product_name,
            "mae": mae_val,
            "rmse": rmse_val,
            "model": model,
            "train_size": len(train),
            "val_size": len(val),
        }

    def predict(
        self,
        product_name: str,
        n_days: int = 7,
    ) -> pd.DataFrame:
        """
        Generate forward predictions for a product.

        Args:
            product_name: Product to predict
            n_days: Number of days to forecast

        Returns:
            DataFrame with columns: [forecast_date, forecasted_quantity, product_name]
        """
        if product_name not in self.models:
            raise ValueError(f"No trained model found for product: {product_name}")

        from darts.metrics import mae

        model = self.models[product_name]
        scaler = self.scalers[product_name]
        series_scaled_full = self.series_scaled[product_name]
        series_unscaled_full = self.series_unscaled[product_name]

        # Forecast future n_days from the end of the series
        pred_scaled = model.predict(
            n=n_days,
            series=series_scaled_full,
        )

        # Inverse transform to original scale
        pred_unscaled = scaler.inverse_transform(pred_scaled)

        # Convert to pandas
        df_forecast = pred_unscaled.pd_dataframe().reset_index()
        df_forecast.columns = ["forecast_date", "forecasted_quantity"]
        df_forecast["product_name"] = product_name

        # (Optional) quick sanity: last observed value vs first forecast
        last_actual = series_unscaled_full[-1:].values()[0][0]
        first_pred = pred_unscaled[0].values()[0][0]
        print(
            f"🔎 {product_name} — last actual: {last_actual:.2f}, "
            f"first forecast: {first_pred:.2f}"
        )

        return df_forecast
