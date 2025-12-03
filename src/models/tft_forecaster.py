"""
Temporal Fusion Transformer (TFT) for advanced time series forecasting.
State-of-the-art deep learning model for multi-horizon forecasting with interpretability.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


class TFTForecaster:
    """
    Temporal Fusion Transformer for multi-product demand forecasting.

    TFT combines high-performance multi-horizon forecasting with interpretable
    insights into temporal dynamics. Perfect for retail/restaurant inventory prediction.
    """

    def __init__(self, data: pd.DataFrame):
        """
        Initialize TFT forecaster with transaction data.

        Args:
            data: DataFrame with columns: date, product, amount, customer_id
        """
        self.data = data.copy()
        self.model = None
        self.training = None
        self.validation = None
        self.predictions = None

    def prepare_data_for_tft(self,
                            max_encoder_length: int = 60,
                            max_prediction_length: int = 30,
                            min_samples_per_product: int = 100) -> Tuple:
        """
        Prepare data in PyTorch Forecasting format for TFT.

        Args:
            max_encoder_length: Number of historical time steps to use
            max_prediction_length: Number of future time steps to predict
            min_samples_per_product: Minimum samples required per product

        Returns:
            Tuple of (training dataset, validation dataset, dataloader)
        """
        try:
            from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
            from pytorch_forecasting.data import GroupNormalizer

            # Aggregate daily sales by product
            df = self.data.copy()
            df['date'] = pd.to_datetime(df['date'])

            # Daily aggregation by product
            daily_data = df.groupby(['date', 'product']).agg({
                'amount': 'sum',
                'customer_id': 'nunique'
            }).reset_index()

            daily_data.columns = ['date', 'product', 'sales', 'num_customers']

            # Filter products with sufficient data
            product_counts = daily_data['product'].value_counts()
            valid_products = product_counts[product_counts >= min_samples_per_product].index
            daily_data = daily_data[daily_data['product'].isin(valid_products)]

            print(f"📊 Training TFT on {len(valid_products)} products with sufficient data")

            # Create complete date range for each product (fill missing dates)
            date_range = pd.date_range(
                start=daily_data['date'].min(),
                end=daily_data['date'].max(),
                freq='D'
            )

            # Fill missing dates for each product
            complete_data = []
            for product in valid_products:
                product_data = daily_data[daily_data['product'] == product].set_index('date')
                product_data = product_data.reindex(date_range, fill_value=0)
                product_data['product'] = product
                product_data['date'] = product_data.index
                complete_data.append(product_data)

            df_complete = pd.concat(complete_data, ignore_index=True)

            # Add temporal features
            df_complete['day_of_week'] = df_complete['date'].dt.dayofweek
            df_complete['day_of_month'] = df_complete['date'].dt.day
            df_complete['week_of_year'] = df_complete['date'].dt.isocalendar().week
            df_complete['month'] = df_complete['date'].dt.month
            df_complete['is_weekend'] = df_complete['day_of_week'].isin([5, 6]).astype(int)

            # Add time index (required by pytorch-forecasting)
            df_complete = df_complete.sort_values(['product', 'date'])
            df_complete['time_idx'] = (df_complete['date'] - df_complete['date'].min()).dt.days

            # Encode products as strings (TFT requires string type for categoricals)
            df_complete['product_id'] = df_complete['product'].astype(str)

            # Split train/validation (80/20)
            max_time_idx = df_complete['time_idx'].max()
            train_cutoff = int(max_time_idx * 0.8)

            # Create TimeSeriesDataSet
            training = TimeSeriesDataSet(
                df_complete[df_complete['time_idx'] <= train_cutoff],
                time_idx='time_idx',
                target='sales',
                group_ids=['product_id'],
                min_encoder_length=max_encoder_length // 2,
                max_encoder_length=max_encoder_length,
                min_prediction_length=1,
                max_prediction_length=max_prediction_length,
                static_categoricals=['product_id'],
                time_varying_known_reals=['time_idx', 'day_of_week', 'month', 'is_weekend'],
                time_varying_unknown_reals=['sales', 'num_customers'],
                target_normalizer=GroupNormalizer(groups=['product_id']),
                add_relative_time_idx=True,
                add_target_scales=True,
                add_encoder_length=True,
            )

            # Create validation dataset
            validation = TimeSeriesDataSet.from_dataset(
                training,
                df_complete,
                predict=True,
                stop_randomization=True
            )

            self.training = training
            self.validation = validation
            # Store product list for forecast output
            self.product_list = df_complete['product'].unique().tolist()

            return training, validation

        except ImportError as e:
            raise ImportError(
                "PyTorch Forecasting not installed. Install with: "
                "pip install pytorch-forecasting torch pytorch-lightning"
            ) from e

    def train_tft(self,
                  max_epochs: int = 30,
                  batch_size: int = 128,
                  learning_rate: float = 0.001,
                  hidden_size: int = 32,
                  attention_head_size: int = 4,
                  dropout: float = 0.1,
                  hidden_continuous_size: int = 16) -> Dict:
        """
        Train Temporal Fusion Transformer model.

        Args:
            max_epochs: Maximum training epochs
            batch_size: Batch size for training
            learning_rate: Learning rate
            hidden_size: Hidden layer size
            attention_head_size: Number of attention heads
            dropout: Dropout rate
            hidden_continuous_size: Hidden size for continuous variables

        Returns:
            Dictionary with training results and model
        """
        try:
            import torch
            from pytorch_forecasting import TemporalFusionTransformer
            from pytorch_lightning import Trainer
            from pytorch_lightning.callbacks import EarlyStopping, LearningRateMonitor
            from torch.utils.data import DataLoader

            print("=" * 70)
            print("🚀 TRAINING TEMPORAL FUSION TRANSFORMER")
            print("=" * 70)

            # Prepare data
            training, validation = self.prepare_data_for_tft()

            # Create dataloaders
            train_dataloader = training.to_dataloader(
                train=True,
                batch_size=batch_size,
                num_workers=0
            )

            val_dataloader = validation.to_dataloader(
                train=False,
                batch_size=batch_size * 4,
                num_workers=0
            )

            # Configure model
            tft = TemporalFusionTransformer.from_dataset(
                training,
                learning_rate=learning_rate,
                hidden_size=hidden_size,
                attention_head_size=attention_head_size,
                dropout=dropout,
                hidden_continuous_size=hidden_continuous_size,
                loss=torch.nn.MSELoss(),
                log_interval=10,
                reduce_on_plateau_patience=4,
            )

            print(f"📊 Model Parameters: {tft.size()/1e3:.1f}k")
            print(f"🔢 Training on {len(training)} samples")
            print(f"✅ Validation on {len(validation)} samples")

            # Setup trainer
            early_stop_callback = EarlyStopping(
                monitor="val_loss",
                min_delta=1e-4,
                patience=5,
                verbose=False,
                mode="min"
            )

            lr_logger = LearningRateMonitor()

            trainer = Trainer(
                max_epochs=max_epochs,
                accelerator="auto",
                gradient_clip_val=0.1,
                callbacks=[lr_logger, early_stop_callback],
                enable_progress_bar=True,
                enable_model_summary=True,
            )

            # Train model
            print("\n🎯 Starting training...")
            trainer.fit(
                tft,
                train_dataloaders=train_dataloader,
                val_dataloaders=val_dataloader,
            )

            # Get best model
            best_model_path = trainer.checkpoint_callback.best_model_path
            best_tft = TemporalFusionTransformer.load_from_checkpoint(best_model_path)

            self.model = best_tft

            print("\n✅ Training complete!")
            print("=" * 70)

            return {
                'model': best_tft,
                'trainer': trainer,
                'training_dataset': training,
                'validation_dataset': validation,
            }

        except Exception as e:
            print(f"❌ Training failed: {str(e)}")
            raise

    def forecast(self, periods: int = 30) -> pd.DataFrame:
        """
        Generate forecasts using trained TFT model.

        Args:
            periods: Number of days to forecast

        Returns:
            DataFrame with forecasts by product
        """
        try:
            if self.model is None:
                raise ValueError("Model not trained. Call train_tft() first.")

            print(f"🔮 Generating {periods}-day forecasts...")

            # Generate predictions
            predictions = self.model.predict(
                self.validation.to_dataloader(
                    train=False,
                    batch_size=128,
                    num_workers=0
                ),
                mode="prediction",
                return_x=True,
            )

            # Extract predictions
            raw_predictions = predictions.output

            # Convert to DataFrame
            forecast_results = []

            for i, product_name in enumerate(self.product_list):
                product_preds = raw_predictions[i].cpu().numpy()

                forecast_results.append({
                    'product': product_name,
                    'forecast': product_preds.tolist(),
                    'mean_forecast': float(product_preds.mean()),
                    'total_forecast': float(product_preds.sum())
                })

            forecast_df = pd.DataFrame(forecast_results)

            self.predictions = forecast_df

            print(f"✅ Forecasts generated for {len(forecast_df)} products")

            return forecast_df

        except Exception as e:
            print(f"❌ Forecasting failed: {str(e)}")
            raise

    def get_variable_importance(self) -> pd.DataFrame:
        """
        Get interpretable variable importance from TFT attention weights.

        Returns:
            DataFrame with variable importance scores
        """
        try:
            if self.model is None:
                raise ValueError("Model not trained. Call train_tft() first.")

            interpretation = self.model.interpret_output(
                self.validation.to_dataloader(
                    train=False,
                    batch_size=128,
                    num_workers=0
                ),
                reduction="sum"
            )

            # Extract attention weights
            attention = interpretation["attention"]

            print("📊 Variable Importance (Attention Weights):")
            print("-" * 50)

            importance_df = pd.DataFrame({
                'variable': list(attention.keys()),
                'importance': list(attention.values())
            }).sort_values('importance', ascending=False)

            for _, row in importance_df.iterrows():
                print(f"  {row['variable']:<30} {row['importance']:.4f}")

            return importance_df

        except Exception as e:
            print(f"⚠️  Could not extract variable importance: {str(e)}")
            return pd.DataFrame()


def create_tft_forecaster(data: pd.DataFrame) -> TFTForecaster:
    """
    Factory function to create and return TFT forecaster.

    Args:
        data: Transaction data

    Returns:
        Configured TFTForecaster instance
    """
    return TFTForecaster(data)
