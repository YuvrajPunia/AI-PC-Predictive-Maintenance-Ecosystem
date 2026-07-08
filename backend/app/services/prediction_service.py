import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from backend.app.config import MODELS_DIR
from backend.app.services.risk_service import RiskService

class PredictionService:
    def __init__(self):
        self.models_dir = MODELS_DIR
        self.models = {}
        self._load_models()

    def _load_models(self):
        """Loads all serialized model binaries at startup."""
        try:
            self.models['feature_engineer'] = joblib.load(os.path.join(self.models_dir, 'feature_engineer.pkl'))
            self.models['problem_preprocessor'] = joblib.load(os.path.join(self.models_dir, 'problem_preprocessor.pkl'))
            self.models['problem_classifier'] = joblib.load(os.path.join(self.models_dir, 'problem_classifier.pkl'))
            
            # Load NLP complaint model
            if os.path.exists(os.path.join(self.models_dir, 'complaint_classifier.pkl')):
                self.models['complaint_vectorizer'] = joblib.load(os.path.join(self.models_dir, 'complaint_vectorizer.pkl'))
                self.models['complaint_classifier'] = joblib.load(os.path.join(self.models_dir, 'complaint_classifier.pkl'))
                
            # Load anomaly
            self.models['anomaly_detector'] = joblib.load(os.path.join(self.models_dir, 'anomaly_detector.pkl'))
            self.models['anomaly_scaler'] = joblib.load(os.path.join(self.models_dir, 'anomaly_scaler.pkl'))
            
            # Load health, failure, RUL regressors/classifiers
            self.models['health_regressor'] = joblib.load(os.path.join(self.models_dir, 'health_regressor.pkl'))
            self.models['failure_risk_regressor'] = joblib.load(os.path.join(self.models_dir, 'failure_risk_regressor.pkl'))
            self.models['failure_classifier'] = joblib.load(os.path.join(self.models_dir, 'failure_classifier.pkl'))
            self.models['rul_regressor'] = joblib.load(os.path.join(self.models_dir, 'rul_regressor.pkl'))
            self.models['explainer'] = joblib.load(os.path.join(self.models_dir, 'explainer.pkl'))
            
            # Load clusterer
            if os.path.exists(os.path.join(self.models_dir, 'fleet_clusterer.pkl')):
                self.models['fleet_clusterer'] = joblib.load(os.path.join(self.models_dir, 'fleet_clusterer.pkl'))
                
            print("PredictionService: All models loaded successfully.")
        except Exception as e:
            print(f"PredictionService: Error loading models: {str(e)}")

    def run_inference(self, pc_row: dict, complaint_text: str, telemetry_history: list = None) -> dict:
        """
        Executes the entire predictive and explainability pipeline.
        Returns a complete structured analysis payload.
        """
        # Ensure models are loaded
        if not self.models:
            self._load_models()

        # 1. Feature Engineering
        fe = self.models.get('feature_engineer')
        df_raw = pd.DataFrame([pc_row])
        df_eng = fe.transform(df_raw)
        
        # Extract features for prediction
        num_features = fe.transform(pd.DataFrame([{
            'CPUUsage': 0, 'RAMUsage': 0, 'Temperature': 0, 'Voltage': 0, 'DiskUsage': 0, 'FanSpeed': 0, 'ModelName': ''
        }])).columns.tolist()
        # Clean model columns list to match trainer numeric feature list
        num_features = [c for c in num_features if c not in ['PC_ID', 'ModelName', 'Department', 'Location', 'LastUpdated', 'ProblemDetected']]
        
        # Preprocessor transformation
        preprocessor = self.models.get('problem_preprocessor')
        X_processed = preprocessor.transform(df_eng)

        # 2. Sensor-Based Multiclass Problem Detection
        cls_model = self.models.get('problem_classifier')
        sensor_pred = cls_model.predict(X_processed)[0]
        sensor_probs = cls_model.predict_proba(X_processed)[0]
        classes = cls_model.classes_
        sensor_conf = float(sensor_probs[list(classes).index(sensor_pred)])

        # 3. Complaint-Based NLP Classification
        complaint_pred = "No Problem"
        complaint_conf = 1.0
        nlp_vectorizer = self.models.get('complaint_vectorizer')
        nlp_cls = self.models.get('complaint_classifier')
        
        if nlp_vectorizer and nlp_cls:
            X_text = nlp_vectorizer.transform([complaint_text])
            complaint_pred = nlp_cls.predict(X_text)[0]
            nlp_probs = nlp_cls.predict_proba(X_text)[0]
            nlp_classes = nlp_cls.classes_
            complaint_conf = float(nlp_probs[list(nlp_classes).index(complaint_pred)])

        # 4. Multimodal Fusion Layer
        if sensor_pred.lower().strip() == complaint_pred.lower().strip():
            agreement_status = "High Agreement"
            final_assessment = sensor_pred
        else:
            agreement_status = "Model Disagreement Detected"
            # Resolve conflict via confidence weight
            if sensor_conf >= complaint_conf:
                final_assessment = sensor_pred
            else:
                final_assessment = complaint_pred

        # 5. Isolation Forest Anomaly Detection
        anom_model = self.models.get('anomaly_detector')
        anom_scaler = self.models.get('anomaly_scaler')
        
        X_anom_raw = df_eng[anom_scaler.feature_names_in_]
        X_anom_scaled = anom_scaler.transform(X_anom_raw)
        
        anom_label_code = anom_model.predict(X_anom_scaled)[0]
        anomaly_label = "Abnormal" if anom_label_code == -1 else "Normal"
        
        # Map decision function score to [0, 1]
        raw_score = float(anom_model.decision_function(X_anom_scaled)[0])
        # Decision function is negative for anomaly, positive for normal.
        # We transform to 0-1 scale: higher score means more anomalous.
        # Simple mapping: normalized = sigmoid(-raw_score * 10.0) or linear bounds
        normalized_anom_score = 1.0 / (1.0 + np.exp(raw_score * 8.0))

        # 6. Health Score Regressor
        health_reg = self.models.get('health_regressor')
        health_score = float(health_reg.predict(X_processed)[0])
        health_score = min(100.0, max(0.0, health_score))
        health_band = RiskService.get_health_band(health_score)

        # 7. Near-Term Failure Risk & WillFailSoon Predictor
        fail_reg = self.models.get('failure_risk_regressor')
        fail_cls = self.models.get('failure_classifier')
        
        failure_risk = float(fail_reg.predict(X_processed)[0])
        failure_risk = min(100.0, max(0.0, failure_risk))
        
        will_fail_soon = int(fail_cls.predict(X_processed)[0]) == 1
        fail_probs = fail_cls.predict_proba(X_processed)[0]
        fail_conf = float(fail_probs[1] if will_fail_soon else fail_probs[0])

        # 8. Remaining Useful Life Regressor
        rul_reg = self.models.get('rul_regressor')
        rul_days = int(rul_reg.predict(X_processed)[0])
        rul_days = max(1, min(365, rul_days))

        # 9. Operational Risk Index
        risk_index, risk_level = RiskService.calculate_risk_index(health_score, failure_risk, normalized_anom_score)

        # 10. Local Explainability
        explainer = self.models.get('explainer')
        top_contribs = explainer.explain_instance(cls_model, X_processed, prediction_type="problem")

        # 11. Telemetry Trend Forecasting
        forecasting = self.run_forecasting(telemetry_history)

        # Extract features for API dictionary format
        eng_features_dict = {}
        for c in df_eng.columns:
            if c in num_features:
                eng_features_dict[c] = float(df_eng[c].iloc[0])

        return {
            "engineered_features": eng_features_dict,
            "problem_analysis": {
                "sensor_prediction": sensor_pred,
                "sensor_confidence": round(sensor_conf * 100.0, 2),
                "complaint_prediction": complaint_pred,
                "complaint_confidence": round(complaint_conf * 100.0, 2),
                "final_assessment": final_assessment,
                "agreement_status": agreement_status
            },
            "predictive_health": {
                "health_score": round(health_score, 1),
                "health_band": health_band,
                "near_term_failure_risk": round(failure_risk, 1),
                "will_fail_soon": will_fail_soon,
                "failure_confidence": round(fail_conf * 100.0, 2),
                "remaining_useful_life_days": rul_days,
                "risk_index": risk_index,
                "risk_level": risk_level
            },
            "anomaly": {
                "label": anomaly_label,
                "score": round(normalized_anom_score, 3)
            },
            "explainability": {
                "method": "Tree SHAP Fallback (Feature-Deviations)",
                "top_contributing_features": top_contribs
            },
            "forecasting": forecasting
        }

    def run_forecasting(self, telemetry_history: list) -> dict:
        """Runs short-horizon linear trend forecasting on Temperature, Voltage, and CPUUsage."""
        if not telemetry_history or len(telemetry_history) < 3:
            return {
                "temperature_forecast": None,
                "voltage_forecast": None,
                "cpu_usage_forecast": None,
                "status": "insufficient_history"
            }

        # Sort telemetry records chronologically
        history = sorted(telemetry_history, key=lambda x: x.timestamp)
        
        # Convert timestamps to numeric float values (unix timestamps)
        times = np.array([h.timestamp.timestamp() for h in history]).reshape(-1, 1)
        
        temps = np.array([h.temperature for h in history])
        volts = np.array([h.voltage for h in history])
        cpus = np.array([h.cpu_usage for h in history])
        
        last_time = history[-1].timestamp
        
        # Project 2 steps into the future (spaced by 1 day)
        future_times_dt = [last_time + timedelta(days=1), last_time + timedelta(days=2)]
        future_times_numeric = np.array([dt.timestamp() for dt in future_times_dt]).reshape(-1, 1)
        
        # Fit models
        temp_model = LinearRegression().fit(times, temps)
        volt_model = LinearRegression().fit(times, volts)
        cpu_model = LinearRegression().fit(times, cpus)
        
        # Predict
        temp_preds = temp_model.predict(future_times_numeric)
        volt_preds = volt_model.predict(future_times_numeric)
        cpu_preds = cpu_model.predict(future_times_numeric)
        
        # Format response
        temp_forecast = []
        volt_forecast = []
        cpu_forecast = []
        
        for idx, dt in enumerate(future_times_dt):
            temp_forecast.append({"timestamp": dt, "value": round(float(temp_preds[idx]), 3)})
            volt_forecast.append({"timestamp": dt, "value": round(float(volt_preds[idx]), 3)})
            cpu_usage = float(cpu_preds[idx])
            # Clip between 0 and 100
            cpu_usage = min(100.0, max(0.0, cpu_usage))
            cpu_forecast.append({"timestamp": dt, "value": round(cpu_usage, 3)})
            
        return {
            "temperature_forecast": temp_forecast,
            "voltage_forecast": volt_forecast,
            "cpu_usage_forecast": cpu_forecast,
            "status": "success"
        }
