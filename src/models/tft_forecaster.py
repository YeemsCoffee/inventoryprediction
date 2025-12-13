"""
Temporal Fusion Transformer (TFT) for demand forecasting using Darts.
Modern, stable implementation with clean API.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


class TFTForecaster:
    """
    Temporal Fusion Transformer using Darts library.
    Handles multi-product demand forecasting with interpretability.
    """

    def __init__(self, data: pd.DataFrame):
        """
        Initialize TFT forecaster.

        Args:
            data: DataFrame with columns: date, product, amount
        """
        self.data = data.copy()
        self.models = {}  # Store model per product
        self.scalers = {}

    def prepare_data_for_product(
        self,
        product_name: str,
        forecast_horizon: int = 7
    ) -> Tuple:
        """
        Prepare time series data for a single product.

        Args:
            product_name: Product to forecast
            forecast_horizon: Days to forecast ahead

        Returns:
            Tuple of (train_series, val_series)
        """
        from darts import TimeSeries
        from sklearn.preprocessing import StandardScaler

        # Filter for this product
        product_data = self.data[self.data['product'] == product_name].copy()

        # Sort by date
        product_data = product_data.sort_values('date')

        # Aggregate by date (sum daily quantities)
        daily_data = product_data.groupby('date')['amount'].sum().reset_index()

        # Fill missing dates
        date_range = pd.date_range(
            start=daily_data['date'].min(),
            end=daily_data['date'].max(),
            freq='D'
        )
        daily_data = daily_data.set_index('date').reindex(date_range, fill_value=0).reset_index()
        daily_data.columns = ['date', 'amount']

        # Create TimeSeries object
        series = TimeSeries.from_dataframe(
            daily_data,
            time_col='date',
            value_cols='amount',
            freq='D'
        )

        # Scale the data
        scaler = StandardScaler()
        scaled_series = series.map(lambda x: scaler.fit_transform(x.reshape(-1, 1)))
        self.scalers[product_name] = scaler

        # Split train/val (80/20)
        split_point = int(len(scaled_series) * 0.8)
        train = scaled_series[:split_point]
        val = scaled_series[split_point:]

        return train, val, series

    def train_tft(
        self,
        product_name: str,
        forecast_horizon: int = 7,
        input_chunk_length: int = 30,
        hidden_size: int = 32,
        num_attention_heads: int = 4,
        dropout: float = 0.1,
        n_epochs: int = 50
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
            Dict with training results
        """
        from darts.models import TFTModel
        from pytorch_lightning.callbacks import EarlyStopping

        print("=" * 70)
        print(f"🚀 TRAINING TFT FOR: {product_name}")
        print("=" * 70)

        try:
            # Prepare data
            train, val, original_series = self.prepare_data_for_product(
                product_name,
                forecast_horizon
            )

            print(f"📊 Training samples: {len(train)}")
            print(f"✅ Validation samples: {len(val)}")

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
                pl_trainer_kwargs={
                    "accelerator": "auto",
                    "callbacks": [
                        EarlyStopping(
                            monitor="val_loss",
                            patience=5,
                            min_delta=1e-4,
                            mode="min"
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
                verbose=True
            )

            # Store model
            self.models[product_name] = model

            # Validate
            prediction = model.predict(n=len(val))

            # Unscale predictions
            scaler = self.scalers[product_name]
            pred_unscaled = prediction.map(
                lambda x: scaler.inverse_transform(x.reshape(-1, 1))
            )
            val_unscaled = val.map(
                lambda x: scaler.inverse_transform(x.reshape(-1, 1))
            )

            # Calculate metrics
            mae = np.mean(np.abs(pred_unscaled.values() - val_unscaled.values()))
            rmse = np.sqrt(np.mean((pred_unscaled.values() - val_unscaled.values()) ** 2))

            print(f"\n✅ Training complete!")
            print(f"📊 Validation MAE: {mae:.2f}")
            print(f"📊 Validation RMSE: {rmse:.2f}")
            print("=" * 70)

            return {
                'product': product_name,
                'mae': mae,
                'rmse': rmse,
                'model': model,
                'train_size': len(train),
                'val_size': len(val)
            }

        except Exception as e:
            print(f"❌ Training failed: {str(e)}")
            raise

    def predict(
        self,
        product_name: str,
        n_days: int = 7
    ) -> pd.DataFrame:
        """
        Generate predictions for a product.

        Args:
            product_name: Product to predict
            n_days: Number of days to forecast

        Returns:
            DataFrame with predictions
        """
        if product_name not in self.models:
            raise ValueError(f"No trained model for {product_name}")

        model = self.models[product_name]

        # Get the last training data point
        _, _, original_series = self.prepare_data_for_product(product_name)

        # Scale
        scaler = self.scalers[product_name]
        scaled_series = original_series.map(
            lambda x: scaler.transform(x.reshape(-1, 1))
        )

        # Predict
        prediction = model.predict(n=n_days, series=scaled_series)

        # Unscale
        pred_unscaled = prediction.map(
            lambda x: scaler.inverse_transform(x.reshape(-1, 1))
        )

        # Convert to DataFrame
        forecast_df = pred_unscaled.pd_dataframe().reset_index()
        forecast_df.columns = ['forecast_date', 'forecasted_quantity']
        forecast_df['product_name'] = product_name

        return forecast_df
