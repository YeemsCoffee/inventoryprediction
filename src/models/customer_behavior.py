"""
Customer behavior prediction and analysis using ML.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class CustomerBehaviorPredictor:
    """Predict customer behavior: churn, lifetime value, next purchase."""

    def __init__(self, data: pd.DataFrame):
        """
        Initialize with transaction data.

        Args:
            data: DataFrame with customer transactions
        """
        self.data = data.copy()
        self.models = {}
        self.scaler = StandardScaler()

    def create_customer_features(self, as_of_date: Optional[str] = None) -> pd.DataFrame:
        """
        Create comprehensive customer features for ML.

        Args:
            as_of_date: Date to calculate features as of (default: latest date)

        Returns:
            DataFrame with customer features
        """
        if as_of_date is None:
            as_of_date = self.data['date'].max()
        else:
            as_of_date = pd.to_datetime(as_of_date)

        # Filter data up to as_of_date
        df = self.data[self.data['date'] <= as_of_date].copy()

        # Calculate RFM features
        customer_features = df.groupby('customer_id').agg({
            'date': [
                ('recency', lambda x: (as_of_date - x.max()).days),
                ('first_purchase', 'min'),
                ('last_purchase', 'max'),
                ('frequency', 'count')
            ],
            'amount': ['sum', 'mean', 'std', 'min', 'max'],
            'product': lambda x: x.nunique()
        })

        customer_features.columns = ['_'.join(col).strip() for col in customer_features.columns.values]
        customer_features = customer_features.reset_index()

        # Calculate additional features
        customer_features['customer_lifetime_days'] = (
            (customer_features['date_last_purchase'] - customer_features['date_first_purchase']).dt.days
        )

        customer_features['purchase_frequency'] = (
            customer_features['date_frequency'] /
            (customer_features['customer_lifetime_days'] + 1)
        )

        # Days since first purchase
        customer_features['days_since_first_purchase'] = (
            (as_of_date - customer_features['date_first_purchase']).dt.days
        )

        # Average days between purchases
        purchase_intervals = df.groupby('customer_id')['date'].apply(
            lambda x: x.sort_values().diff().dt.days.mean()
        )
        customer_features = customer_features.merge(
            purchase_intervals.rename('avg_days_between_purchases'),
            left_on='customer_id',
            right_index=True,
            how='left'
        )

        # Fill NaN values
        customer_features['avg_days_between_purchases'] = customer_features['avg_days_between_purchases'].fillna(
            customer_features['customer_lifetime_days']
        )
        customer_features['amount_std'] = customer_features['amount_std'].fillna(0)

        # Add revenue if price column exists
        if 'price' in df.columns:
            revenue = df.groupby('customer_id')['price'].sum()
            customer_features = customer_features.merge(
                revenue.rename('total_revenue'),
                left_on='customer_id',
                right_index=True,
                how='left'
            )

        return customer_features

    def predict_churn(self, threshold_days: int = 60, train_model: bool = True) -> pd.DataFrame:
        """
        Predict which customers are likely to churn.

        Args:
            threshold_days: Days of inactivity to consider churned
            train_model: Whether to train a new model

        Returns:
            DataFrame with churn predictions
        """
        customer_features = self.create_customer_features()

        # Define churn (simplified: if recency > threshold)
        customer_features['churned'] = (
            customer_features['date_recency'] > threshold_days
        ).astype(int)

        # Features for model
        feature_cols = [
            'date_frequency', 'amount_sum', 'amount_mean', 'amount_std',
            'product_<lambda>', 'customer_lifetime_days', 'purchase_frequency',
            'avg_days_between_purchases'
        ]

        # Filter to existing columns
        feature_cols = [col for col in feature_cols if col in customer_features.columns]

        X = customer_features[feature_cols].fillna(0)
        y = customer_features['churned']

        if train_model:
            # Train churn prediction model
            print("🎯 Training churn prediction model...")

            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )

            # Use stratified split
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            model.fit(X_train, y_train)

            # Evaluate
            train_score = model.score(X_train, y_train)
            test_score = model.score(X_test, y_test)

            print(f"✅ Churn model trained - Train Acc: {train_score:.3f}, Test Acc: {test_score:.3f}")

            self.models['churn'] = {
                'model': model,
                'feature_cols': feature_cols,
                'threshold_days': threshold_days
            }

            # Predict probabilities
            churn_proba = model.predict_proba(X)[:, 1]

        else:
            # Use existing model
            if 'churn' not in self.models:
                raise ValueError("No trained churn model. Set train_model=True")

            model = self.models['churn']['model']
            churn_proba = model.predict_proba(X)[:, 1]

        # Add predictions to customer features
        customer_features['churn_probability'] = churn_proba
        customer_features['churn_risk'] = pd.cut(
            churn_proba,
            bins=[0, 0.3, 0.7, 1.0],
            labels=['Low', 'Medium', 'High']
        )

        return customer_features[[
            'customer_id', 'date_recency', 'date_frequency',
            'churn_probability', 'churn_risk'
        ]]

    def predict_next_purchase(self) -> pd.DataFrame:
        """
        Predict when customers are likely to make their next purchase.

        Returns:
            DataFrame with next purchase predictions
        """
        customer_features = self.create_customer_features()

        # Calculate expected days to next purchase
        # Using average days between purchases
        customer_features['expected_next_purchase_days'] = (
            customer_features['avg_days_between_purchases']
        )

        customer_features['expected_next_purchase_date'] = (
            customer_features['date_last_purchase'] +
            pd.to_timedelta(customer_features['expected_next_purchase_days'], unit='D')
        )

        # Probability they'll purchase soon
        customer_features['likely_to_purchase_soon'] = (
            customer_features['date_recency'] >=
            customer_features['avg_days_between_purchases'] * 0.8
        )

        return customer_features[[
            'customer_id',
            'date_last_purchase',
            'avg_days_between_purchases',
            'expected_next_purchase_date',
            'likely_to_purchase_soon'
        ]]

    def calculate_customer_lifetime_value(self, months_ahead: int = 12) -> pd.DataFrame:
        """
        Predict customer lifetime value.

        Args:
            months_ahead: Number of months to project

        Returns:
            DataFrame with CLV predictions
        """
        customer_features = self.create_customer_features()

        # Calculate historical CLV
        if 'total_revenue' in customer_features.columns:
            avg_order_value = customer_features['total_revenue'] / customer_features['date_frequency']
        else:
            avg_order_value = customer_features['amount_mean']

        # Project future value
        # Estimated purchases in next period
        estimated_purchases = (
            customer_features['purchase_frequency'] * 30 * months_ahead
        )

        customer_features['predicted_clv'] = avg_order_value * estimated_purchases

        customer_features['clv_segment'] = pd.qcut(
            customer_features['predicted_clv'],
            q=5,
            labels=['Very Low', 'Low', 'Medium', 'High', 'Very High']
        )

        return customer_features[[
            'customer_id',
            'date_frequency',
            'purchase_frequency',
            'predicted_clv',
            'clv_segment'
        ]]

    def identify_high_value_customers(self, top_pct: float = 0.2) -> pd.DataFrame:
        """
        Identify high-value customers (top X%).

        Args:
            top_pct: Top percentage to identify (0.2 = top 20%)

        Returns:
            DataFrame with high-value customers
        """
        clv = self.calculate_customer_lifetime_value()

        threshold = clv['predicted_clv'].quantile(1 - top_pct)
        high_value = clv[clv['predicted_clv'] >= threshold].copy()

        high_value = high_value.sort_values('predicted_clv', ascending=False)

        return high_value

    def get_at_risk_high_value_customers(self) -> pd.DataFrame:
        """
        Find high-value customers at risk of churning.

        Returns:
            DataFrame with at-risk high-value customers
        """
        # Get high-value customers
        high_value = self.identify_high_value_customers(top_pct=0.2)

        # Get churn predictions
        churn_pred = self.predict_churn(train_model=True)

        # Merge
        at_risk = high_value.merge(
            churn_pred,
            on='customer_id',
            how='inner'
        )

        # Filter to high churn risk
        at_risk = at_risk[at_risk['churn_risk'].isin(['Medium', 'High'])]

        at_risk = at_risk.sort_values('predicted_clv', ascending=False)

        return at_risk[[
            'customer_id', 'predicted_clv', 'churn_probability',
            'churn_risk', 'date_recency'
        ]]

    def get_customer_insights_summary(self) -> Dict:
        """
        Generate comprehensive customer insights summary.

        Returns:
            Dictionary with key insights
        """
        print("📊 Generating customer insights...")

        customer_features = self.create_customer_features()
        churn_pred = self.predict_churn(train_model=True)
        clv = self.calculate_customer_lifetime_value()
        at_risk_hv = self.get_at_risk_high_value_customers()

        insights = {
            'total_customers': len(customer_features),
            'active_customers': len(customer_features[customer_features['date_recency'] <= 30]),
            'at_risk_customers': len(churn_pred[churn_pred['churn_risk'] == 'High']),
            'churned_customers': len(churn_pred[churn_pred['churn_risk'] == 'High']),
            'high_value_customers': len(self.identify_high_value_customers()),
            'at_risk_high_value': len(at_risk_hv),
            'avg_customer_lifetime_days': customer_features['customer_lifetime_days'].mean(),
            'avg_purchase_frequency': customer_features['purchase_frequency'].mean(),
            'predicted_clv_total': clv['predicted_clv'].sum(),
            'top_customers_by_clv': self.identify_high_value_customers(top_pct=0.1)[
                ['customer_id', 'predicted_clv']
            ].head(10).to_dict('records')
        }

        print("✅ Insights generated!")

        return insights
