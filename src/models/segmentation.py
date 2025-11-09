"""
Customer segmentation using machine learning clustering algorithms.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA


class CustomerSegmentation:
    """Segment customers based on their behavior patterns."""

    def __init__(self, data: pd.DataFrame):
        """
        Initialize with customer transaction data.

        Args:
            data: DataFrame with customer transactions
        """
        self.data = data.copy()
        self.customer_features = None
        self.scaler = StandardScaler()
        self.model = None
        self.segments = None

    def create_customer_features(self) -> pd.DataFrame:
        """
        Create features for each customer for segmentation.

        Returns:
            DataFrame with customer features
        """
        # Calculate RFM (Recency, Frequency, Monetary) metrics
        current_date = self.data['date'].max()

        customer_features = self.data.groupby('customer_id').agg({
            'date': lambda x: (current_date - x.max()).days,  # Recency
            'amount': ['sum', 'mean', 'std', 'count'],  # Monetary and Frequency
            'product': lambda x: x.nunique()  # Product diversity
        })

        customer_features.columns = ['recency_days', 'total_items', 'avg_items',
                                     'std_items', 'transaction_count', 'product_diversity']

        # Fill NaN in std_items (customers with only one transaction)
        customer_features['std_items'] = customer_features['std_items'].fillna(0)

        # Calculate customer lifetime (days since first purchase)
        first_purchase = self.data.groupby('customer_id')['date'].min()
        customer_features['lifetime_days'] = (
            (current_date - first_purchase).dt.days
        )

        # Calculate purchase frequency (transactions per day)
        customer_features['purchase_frequency'] = (
            customer_features['transaction_count'] /
            (customer_features['lifetime_days'] + 1)
        )

        # Add revenue if price column exists
        if 'price' in self.data.columns:
            revenue = self.data.groupby('customer_id')['price'].sum()
            customer_features['total_revenue'] = revenue
            customer_features['avg_revenue'] = (
                customer_features['total_revenue'] /
                customer_features['transaction_count']
            )

        self.customer_features = customer_features
        return customer_features

    def perform_kmeans_segmentation(self, n_clusters: int = 4,
                                   features: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Segment customers using K-Means clustering.

        Args:
            n_clusters: Number of customer segments
            features: List of features to use (if None, uses key RFM features)

        Returns:
            DataFrame with customer segments
        """
        if self.customer_features is None:
            self.create_customer_features()

        # Select features for clustering
        if features is None:
            features = ['recency_days', 'total_items', 'transaction_count',
                       'purchase_frequency', 'product_diversity']

        # Filter to only existing features
        features = [f for f in features if f in self.customer_features.columns]

        X = self.customer_features[features].copy()

        # Handle any remaining NaN values
        X = X.fillna(0)

        # Adjust n_clusters if we have fewer samples than clusters
        n_samples = len(X)
        if n_samples < n_clusters:
            n_clusters = max(1, n_samples)  # At least 1 cluster
            print(f"⚠️  Adjusting clusters from 4 to {n_clusters} (only {n_samples} customers)")

        # Standardize features
        X_scaled = self.scaler.fit_transform(X)

        # Perform K-Means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)

        self.model = kmeans
        self.customer_features['segment'] = clusters

        return self.customer_features

    def analyze_segments(self) -> pd.DataFrame:
        """
        Analyze characteristics of each customer segment.

        Returns:
            DataFrame with segment statistics
        """
        if self.customer_features is None or 'segment' not in self.customer_features.columns:
            raise ValueError("Run perform_kmeans_segmentation first")

        segment_stats = self.customer_features.groupby('segment').agg({
            'recency_days': ['mean', 'median'],
            'total_items': ['mean', 'median'],
            'transaction_count': ['mean', 'median'],
            'purchase_frequency': ['mean', 'median'],
            'product_diversity': ['mean', 'median']
        }).round(2)

        # Flatten column names
        segment_stats.columns = ['_'.join(col).strip() for col in segment_stats.columns.values]

        # Add customer count per segment
        segment_counts = self.customer_features.groupby('segment').size()
        segment_stats['customer_count'] = segment_counts

        # Calculate percentage
        total_customers = len(self.customer_features)
        segment_stats['percentage'] = (
            (segment_stats['customer_count'] / total_customers * 100).round(2)
        )

        return segment_stats.reset_index()

    def label_segments(self) -> Dict[int, str]:
        """
        Assign meaningful labels to segments based on their characteristics.

        Returns:
            Dictionary mapping segment numbers to labels
        """
        if self.customer_features is None or 'segment' not in self.customer_features.columns:
            raise ValueError("Run perform_kmeans_segmentation first")

        segment_stats = self.customer_features.groupby('segment').agg({
            'recency_days': 'mean',
            'total_items': 'mean',
            'transaction_count': 'mean',
            'purchase_frequency': 'mean'
        })

        labels = {}

        for segment in segment_stats.index:
            stats = segment_stats.loc[segment]

            # Determine segment label based on characteristics
            if stats['purchase_frequency'] > segment_stats['purchase_frequency'].median() and \
               stats['total_items'] > segment_stats['total_items'].median():
                labels[segment] = 'High Value'
            elif stats['recency_days'] < segment_stats['recency_days'].median() and \
                 stats['transaction_count'] > segment_stats['transaction_count'].median():
                labels[segment] = 'Loyal Customers'
            elif stats['recency_days'] > segment_stats['recency_days'].median() * 1.5:
                labels[segment] = 'At Risk'
            elif stats['transaction_count'] <= 2:
                labels[segment] = 'New Customers'
            else:
                labels[segment] = 'Regular Customers'

        return labels

    def get_segment_recommendations(self) -> List[Dict]:
        """
        Generate recommendations for each customer segment.

        Returns:
            List of recommendation dictionaries
        """
        segment_labels = self.label_segments()
        segment_stats = self.analyze_segments()

        recommendations = []

        for _, segment_data in segment_stats.iterrows():
            segment_id = segment_data['segment']
            label = segment_labels.get(segment_id, f'Segment {segment_id}')

            # Generate segment-specific recommendations
            if label == 'High Value':
                recommendation = 'VIP treatment, exclusive offers, early access to new products'
            elif label == 'Loyal Customers':
                recommendation = 'Loyalty rewards, thank you messages, maintain quality service'
            elif label == 'At Risk':
                recommendation = 'Re-engagement campaigns, win-back offers, survey for feedback'
            elif label == 'New Customers':
                recommendation = 'Welcome offers, onboarding emails, product education'
            else:
                recommendation = 'Regular engagement, special promotions, encourage repeat purchases'

            recommendations.append({
                'segment_id': int(segment_id),
                'segment_label': label,
                'customer_count': int(segment_data['customer_count']),
                'percentage': float(segment_data['percentage']),
                'recommendation': recommendation
            })

        return recommendations

    def predict_segment(self, customer_features: Dict) -> int:
        """
        Predict which segment a new customer belongs to.

        Args:
            customer_features: Dictionary with customer feature values

        Returns:
            Segment ID
        """
        if self.model is None:
            raise ValueError("Train the model first using perform_kmeans_segmentation")

        # Create feature vector
        feature_names = ['recency_days', 'total_items', 'transaction_count',
                        'purchase_frequency', 'product_diversity']

        X = np.array([customer_features.get(f, 0) for f in feature_names]).reshape(1, -1)

        # Standardize
        X_scaled = self.scaler.transform(X)

        # Predict
        segment = self.model.predict(X_scaled)[0]

        return int(segment)

    def visualize_segments_pca(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Reduce features to 2D using PCA for visualization.

        Returns:
            Tuple of (coordinates, segments)
        """
        if self.customer_features is None or 'segment' not in self.customer_features.columns:
            raise ValueError("Run perform_kmeans_segmentation first")

        features = ['recency_days', 'total_items', 'transaction_count',
                   'purchase_frequency', 'product_diversity']
        features = [f for f in features if f in self.customer_features.columns]

        X = self.customer_features[features].fillna(0)
        X_scaled = self.scaler.fit_transform(X)

        # Apply PCA
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)

        return X_pca, self.customer_features['segment'].values
