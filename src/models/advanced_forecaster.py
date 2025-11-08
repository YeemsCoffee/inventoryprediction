"""
Advanced forecasting models using Deep Learning and ML ensembles.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class AdvancedForecaster:
    """Advanced forecasting with LSTM, XGBoost, and ensemble methods."""

    def __init__(self, data: pd.DataFrame):
        """
        Initialize with historical data.

        Args:
            data: DataFrame with time series data
        """
        self.data = data.copy()
        self.models = {}
        self.scaler = None

    def prepare_lstm_data(self, series: pd.Series, lookback: int = 30) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare data for LSTM model.

        Args:
            series: Time series data
            lookback: Number of previous time steps to use

        Returns:
            Tuple of (X, y) arrays
        """
        from sklearn.preprocessing import MinMaxScaler

        # Scale data
        self.scaler = MinMaxScaler()
        scaled_data = self.scaler.fit_transform(series.values.reshape(-1, 1))

        X, y = [], []
        for i in range(lookback, len(scaled_data)):
            X.append(scaled_data[i-lookback:i, 0])
            y.append(scaled_data[i, 0])

        return np.array(X), np.array(y)

    def build_lstm_model(self, input_shape: Tuple[int, int]) -> 'keras.Model':
        """
        Build LSTM neural network for time series forecasting.

        Args:
            input_shape: Shape of input data

        Returns:
            Compiled Keras model
        """
        try:
            from tensorflow import keras
            from tensorflow.keras import layers

            model = keras.Sequential([
                layers.LSTM(128, return_sequences=True, input_shape=input_shape),
                layers.Dropout(0.2),
                layers.LSTM(64, return_sequences=True),
                layers.Dropout(0.2),
                layers.LSTM(32),
                layers.Dropout(0.2),
                layers.Dense(16, activation='relu'),
                layers.Dense(1)
            ])

            model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            return model

        except ImportError:
            print("⚠️  TensorFlow not available. Install with: pip install tensorflow")
            return None

    def train_lstm_forecast(self, date_column: str = 'date',
                           value_column: str = 'amount',
                           lookback: int = 30,
                           epochs: int = 50,
                           frequency: str = 'D') -> Dict:
        """
        Train LSTM model for demand forecasting.

        Args:
            date_column: Date column name
            value_column: Value column to forecast
            lookback: Number of previous days to consider
            epochs: Number of training epochs
            frequency: Data frequency

        Returns:
            Dictionary with model and training history
        """
        try:
            from tensorflow import keras

            # Aggregate data by frequency
            df = self.data.copy()
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.set_index(date_column)

            ts = df[value_column].resample(frequency).sum()

            # Prepare data
            X, y = self.prepare_lstm_data(ts, lookback)

            # Reshape for LSTM [samples, time steps, features]
            X = X.reshape((X.shape[0], X.shape[1], 1))

            # Train/test split
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # Build and train model
            model = self.build_lstm_model((X_train.shape[1], 1))

            if model is None:
                return {'error': 'Could not build LSTM model'}

            print("🧠 Training LSTM model...")
            history = model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=32,
                validation_data=(X_test, y_test),
                verbose=0
            )

            self.models['lstm'] = model

            # Evaluate
            train_loss = history.history['loss'][-1]
            val_loss = history.history['val_loss'][-1]

            print(f"✅ LSTM trained - Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

            return {
                'model': model,
                'history': history,
                'train_loss': train_loss,
                'val_loss': val_loss,
                'lookback': lookback
            }

        except Exception as e:
            print(f"❌ LSTM training failed: {str(e)}")
            return {'error': str(e)}

    def forecast_lstm(self, periods: int = 30, lookback: int = 30) -> pd.DataFrame:
        """
        Generate forecast using trained LSTM model.

        Args:
            periods: Number of periods to forecast
            lookback: Lookback window (must match training)

        Returns:
            DataFrame with forecast
        """
        if 'lstm' not in self.models:
            return pd.DataFrame({'error': ['Train LSTM model first']})

        try:
            from sklearn.preprocessing import MinMaxScaler

            model = self.models['lstm']

            # Get last lookback values
            last_sequence = self.scaler.transform(
                self.data['amount'].tail(lookback).values.reshape(-1, 1)
            )

            predictions = []
            current_sequence = last_sequence.reshape(1, lookback, 1)

            for _ in range(periods):
                # Predict next value
                next_pred = model.predict(current_sequence, verbose=0)[0, 0]
                predictions.append(next_pred)

                # Update sequence
                current_sequence = np.roll(current_sequence, -1, axis=1)
                current_sequence[0, -1, 0] = next_pred

            # Inverse transform predictions
            predictions = self.scaler.inverse_transform(
                np.array(predictions).reshape(-1, 1)
            )

            # Create forecast dataframe
            last_date = self.data['date'].max()
            future_dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1),
                periods=periods,
                freq='D'
            )

            forecast_df = pd.DataFrame({
                'ds': future_dates,
                'yhat': predictions.flatten()
            })

            return forecast_df

        except Exception as e:
            print(f"❌ LSTM forecast failed: {str(e)}")
            return pd.DataFrame({'error': [str(e)]})

    def train_xgboost_forecast(self, date_column: str = 'date',
                               value_column: str = 'amount',
                               frequency: str = 'D') -> Dict:
        """
        Train XGBoost model for forecasting.

        Args:
            date_column: Date column name
            value_column: Value to forecast
            frequency: Data frequency

        Returns:
            Dictionary with trained model
        """
        try:
            import xgboost as xgb

            # Aggregate data
            df = self.data.copy()
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.set_index(date_column)

            ts = df[value_column].resample(frequency).sum().reset_index()
            ts.columns = ['date', 'value']

            # Create features
            ts['day_of_week'] = ts['date'].dt.dayofweek
            ts['day_of_month'] = ts['date'].dt.day
            ts['month'] = ts['date'].dt.month
            ts['quarter'] = ts['date'].dt.quarter
            ts['year'] = ts['date'].dt.year

            # Lag features
            for lag in [1, 7, 14, 30]:
                ts[f'lag_{lag}'] = ts['value'].shift(lag)

            # Rolling features
            ts['rolling_mean_7'] = ts['value'].rolling(window=7).mean()
            ts['rolling_std_7'] = ts['value'].rolling(window=7).std()

            # Drop NaN
            ts = ts.dropna()

            # Features and target
            feature_cols = [col for col in ts.columns if col not in ['date', 'value']]
            X = ts[feature_cols]
            y = ts['value']

            # Train/test split
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # Train XGBoost
            print("🚀 Training XGBoost model...")
            model = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=7,
                learning_rate=0.05,
                random_state=42
            )

            model.fit(X_train, y_train)

            # Evaluate
            train_score = model.score(X_train, y_train)
            test_score = model.score(X_test, y_test)

            self.models['xgboost'] = {
                'model': model,
                'feature_cols': feature_cols,
                'last_data': ts
            }

            print(f"✅ XGBoost trained - Train R²: {train_score:.4f}, Test R²: {test_score:.4f}")

            return {
                'model': model,
                'train_score': train_score,
                'test_score': test_score,
                'feature_importance': dict(zip(feature_cols, model.feature_importances_))
            }

        except ImportError:
            print("⚠️  XGBoost not available. Install with: pip install xgboost")
            return {'error': 'XGBoost not installed'}
        except Exception as e:
            print(f"❌ XGBoost training failed: {str(e)}")
            return {'error': str(e)}

    def ensemble_forecast(self, periods: int = 30,
                         models: List[str] = ['prophet', 'xgboost', 'lstm']) -> pd.DataFrame:
        """
        Create ensemble forecast from multiple models.

        Args:
            periods: Number of periods to forecast
            models: List of models to ensemble

        Returns:
            DataFrame with ensemble forecast
        """
        forecasts = []

        # Collect forecasts from each model
        if 'prophet' in models and 'prophet' in self.models:
            # Would need Prophet integration
            pass

        if 'xgboost' in models and 'xgboost' in self.models:
            # Would need XGBoost forecast implementation
            pass

        if 'lstm' in models and 'lstm' in self.models:
            lstm_forecast = self.forecast_lstm(periods)
            if not lstm_forecast.empty and 'error' not in lstm_forecast.columns:
                forecasts.append(lstm_forecast['yhat'].values)

        if not forecasts:
            return pd.DataFrame({'message': ['No trained models available']})

        # Average ensemble
        ensemble_predictions = np.mean(forecasts, axis=0)

        # Create forecast dataframe
        last_date = self.data['date'].max()
        future_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=periods,
            freq='D'
        )

        return pd.DataFrame({
            'ds': future_dates,
            'yhat': ensemble_predictions,
            'yhat_lower': ensemble_predictions * 0.85,
            'yhat_upper': ensemble_predictions * 1.15
        })
