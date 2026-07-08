import numpy as np
import pandas as pd
import os
import joblib

class PCExplainer:
    def __init__(self, feature_names):
        self.feature_names = feature_names
        self.median_values = {}
        # Default nominal baselines for healthy PCs
        self.healthy_baselines = {
            'CPUUsage': 30.0,
            'RAMUsage': 40.0,
            'Temperature': 45.0,
            'Voltage': 15.0,
            'DiskUsage': 35.0,
            'FanSpeed': 2500.0,
            'TemperatureStress': 0.0,
            'VoltageDeviation': 0.0,
            'CombinedLoad': 34.0,
            'ResourcePressureIndex': 35.0,
            'CoolingEfficiencyProxy': 55.0,
            'FanTemperatureMismatch': 0.0,
            'ThermalLoadRatio': 1.0,
            'PowerInstabilityIndex': 0.0,
            'DiskStressIndex': 28.0,
            'CPU_Temp_Interaction': 1350.0,
            'RAM_CPU_Interaction': 1200.0,
            'Temp_VoltageDev_Interaction': 0.0,
            'Temp_FanSpeed_Ratio': 0.018,
            'Disk_CPU_Interaction': 1050.0,
            'DegradationSeverityIndex': 0.0
        }

    def explain_instance(self, model, X_instance: np.ndarray, prediction_type="health") -> list:
        """
        Generates local explanation for a single prediction instance.
        Returns a list of dicts: [{'feature': str, 'value': float, 'direction': str, 'magnitude': float}]
        """
        # Try to use SHAP if installed
        try:
            import shap
            # We can use TreeExplainer for Random Forest / Gradient Boosting models
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_instance)
            
            # Extract shap values for this instance
            if isinstance(shap_values, list):
                # Multiclass classifier case (shap_values is list per class)
                # We explain the predicted class
                pred_class = int(model.predict(X_instance)[0])
                instance_shap = shap_values[pred_class][0]
            elif len(shap_values.shape) == 3:
                # Some newer SHAP versions return (n_samples, n_features, n_classes)
                pred_class = int(model.predict(X_instance)[0])
                instance_shap = shap_values[0, :, pred_class]
            else:
                # Regressor case
                instance_shap = shap_values[0]
                
            explanations = []
            for idx, col in enumerate(self.feature_names):
                val = float(X_instance[0, idx])
                shap_val = float(instance_shap[idx])
                direction = "Positive" if shap_val > 0 else "Negative"
                explanations.append({
                    "feature": col,
                    "value": round(val, 3),
                    "direction": direction,
                    "magnitude": round(abs(shap_val), 4)
                })
            # Sort by absolute magnitude descending
            explanations.sort(key=lambda x: x["magnitude"], reverse=True)
            return explanations[:5]
            
        except Exception as e:
            # Fallback local attribution: Feature-importance weighted deviation
            # we calculate how much the current feature deviates from its healthy baseline,
            # and multiply it by the model's feature importance.
            explanations = []
            
            # Fetch model feature importances
            feature_importances = np.ones(len(self.feature_names)) / len(self.feature_names)
            if hasattr(model, 'feature_importances_'):
                feature_importances = model.feature_importances_
            elif hasattr(model, 'coef_'):
                # Handle linear models
                coefs = model.coef_
                if len(coefs.shape) > 1:  # Multiclass
                    feature_importances = np.abs(coefs).mean(axis=0)
                else:
                    feature_importances = np.abs(coefs)
                # Normalize to sum to 1
                if feature_importances.sum() > 0:
                    feature_importances = feature_importances / feature_importances.sum()
                    
            for idx, col in enumerate(self.feature_names):
                val = float(X_instance[0, idx])
                baseline = self.healthy_baselines.get(col, self.median_values.get(col, 0.0))
                
                # Compute deviation
                std_dev = abs(val - baseline)
                # Add tiny epsilon to avoid zero division
                denom = max(1.0, abs(baseline))
                rel_dev = std_dev / denom
                
                # Local contribution score = relative deviation * feature importance
                magnitude = rel_dev * feature_importances[idx]
                
                # Determine direction (does it push health down or up?)
                # If health regression: higher stress features push it Down
                # If problem detection or failure risk: higher stress features push it Up
                is_stress_feature = any(term in col for term in ['Stress', 'Deviation', 'Mismatch', 'Usage', 'Ratio', 'Interaction', 'Severity', 'Pressure'])
                
                if prediction_type == "health":
                    # For health, elevated stress pushes health down (Negative direction)
                    direction = "Negative" if val > baseline and is_stress_feature else "Positive"
                else:
                    # For failure risk or problem, elevated stress pushes risk up (Positive direction)
                    direction = "Positive" if val > baseline and is_stress_feature else "Negative"
                    
                explanations.append({
                    "feature": col,
                    "value": round(val, 3),
                    "direction": direction,
                    "magnitude": round(magnitude, 4)
                })
                
            explanations.sort(key=lambda x: x["magnitude"], reverse=True)
            return explanations[:5]
            
    def save(self, folder_path: str):
        os.makedirs(folder_path, exist_ok=True)
        joblib.dump(self, os.path.join(folder_path, 'explainer.pkl'))
        print("Explainer state saved successfully.")
