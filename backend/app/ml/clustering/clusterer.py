import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import os
import joblib

class PCClusterer:
    def __init__(self, n_clusters=4, random_state=42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init='auto')
        self.cluster_labels = {}  # cluster index -> human readable name
        self.is_fit = False

    def fit(self, df_features: pd.DataFrame, feature_cols: list):
        """Fits the scaler and KMeans clusterer on PC sensor & engineered features."""
        X = df_features[feature_cols].copy()
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit KMeans
        self.kmeans.fit(X_scaled)
        self.is_fit = True
        
        # Analyze centroids to map cluster numbers to human-readable tags
        centroids = self.kmeans.cluster_centers_
        # Centroids are in scaled space, let's inverse transform to read original scale
        original_centroids = self.scaler.inverse_transform(centroids)
        
        for idx in range(self.n_clusters):
            centroid_row = dict(zip(feature_cols, original_centroids[idx]))
            
            # Label heuristic rules based on original features
            temp = centroid_row.get('Temperature', 45.0)
            cpu = centroid_row.get('CPUUsage', 25.0)
            ram = centroid_row.get('RAMUsage', 35.0)
            volt_dev = centroid_row.get('VoltageDeviation', 0.0)
            fan = centroid_row.get('FanSpeed', 2500.0)
            
            if temp > 70.0 or centroid_row.get('TemperatureStress', 0.0) > 5.0:
                self.cluster_labels[idx] = "Elevated-Thermal Profile"
            elif cpu > 70.0 or ram > 75.0 or centroid_row.get('CombinedLoad', 0.0) > 70.0:
                self.cluster_labels[idx] = "High-Utilization Profile"
            elif volt_dev > 1.5 or centroid_row.get('PowerInstabilityIndex', 0.0) > 0.5:
                self.cluster_labels[idx] = "Voltage-Instability Profile"
            else:
                self.cluster_labels[idx] = "Stable / Lower-Stress Profile"
                
        return self

    def predict(self, df_features: pd.DataFrame, feature_cols: list) -> tuple:
        """Predicts cluster indexes and returns (cluster_indexes, cluster_names)."""
        if not self.is_fit:
            raise ValueError("Clusterer has not been fitted yet.")
        X = df_features[feature_cols].copy()
        X_scaled = self.scaler.transform(X)
        preds = self.kmeans.predict(X_scaled)
        
        names = [self.cluster_labels[int(p)] for p in preds]
        return preds.tolist(), names

    def predict_single(self, row_dict: dict, feature_cols: list) -> tuple:
        """Predicts cluster for a single PC observation."""
        df_single = pd.DataFrame([row_dict])
        preds, names = self.predict(df_single, feature_cols)
        return int(preds[0]), names[0]

    def save(self, folder_path: str):
        os.makedirs(folder_path, exist_ok=True)
        joblib.dump(self, os.path.join(folder_path, 'fleet_clusterer.pkl'))
        print("Fleet clusterer saved successfully.")
