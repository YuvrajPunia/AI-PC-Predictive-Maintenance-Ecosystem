import numpy as np
from sklearn.covariance import LedoitWolf

class RobustMahalanobisOOD:
    def __init__(self):
        self.mean_ = None
        self.precision_ = None
        self.threshold_ = None

    def fit(self, X):
        """Fits mean and Ledoit-Wolf shrinkage covariance precision matrix."""
        self.mean_ = np.mean(X, axis=0)
        lw = LedoitWolf()
        lw.fit(X)
        self.precision_ = lw.precision_
        
        # Calculate training distances to set threshold
        train_dists = self.compute_distance(X)
        # Set threshold at 97.5th percentile
        self.threshold_ = float(np.percentile(train_dists, 97.5))

    def compute_distance(self, X):
        """Computes Mahalanobis distance for each instance in X."""
        X_diff = X - self.mean_
        dist = np.sqrt(np.sum(np.dot(X_diff, self.precision_) * X_diff, axis=1))
        return dist

    def predict_ood(self, X):
        """Returns True if instance distance exceeds threshold, else False."""
        dists = self.compute_distance(X)
        return dists > self.threshold_
