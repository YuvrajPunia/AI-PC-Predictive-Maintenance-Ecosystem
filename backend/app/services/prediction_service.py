import os
import joblib
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from backend.app.config import MODELS_DIR
from backend.app.services.risk_service import RiskService
from backend.app.ml.ood_detector import RobustMahalanobisOOD

class PredictionService:
    def __init__(self):
        self.models_dir = MODELS_DIR
        self.models = {}
        self._load_models()

    def _load_models(self):
        """Loads all active serialized model binaries at startup."""
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
            
            # Load OOD detector
            if os.path.exists(os.path.join(self.models_dir, 'ood_detector.pkl')):
                self.models['ood_detector'] = joblib.load(os.path.join(self.models_dir, 'ood_detector.pkl'))
                self.models['ood_scaler'] = joblib.load(os.path.join(self.models_dir, 'ood_scaler.pkl'))
                with open(os.path.join(self.models_dir, 'ood_metadata.json'), 'r') as f:
                    self.models['ood_metadata'] = json.load(f)
                    
            self.models['explainer'] = joblib.load(os.path.join(self.models_dir, 'explainer.pkl'))
            
            # Load clusterer
            if os.path.exists(os.path.join(self.models_dir, 'fleet_clusterer.pkl')):
                self.models['fleet_clusterer'] = joblib.load(os.path.join(self.models_dir, 'fleet_clusterer.pkl'))
                
            print("PredictionService: Active models loaded successfully.")
        except Exception as e:
            print(f"PredictionService: Error loading models: {str(e)}")

    def run_inference(self, pc_row: dict, complaint_text: str, telemetry_history: list = None, explain: bool = True) -> dict:
        """
        Executes the entire predictive and explainability pipeline.
        Returns a complete structured analysis payload with deterministic safety indicators.
        """
        # Ensure models are loaded
        if not self.models:
            self._load_models()

        # 1. Feature Engineering
        fe = self.models.get('feature_engineer')
        df_raw = pd.DataFrame([pc_row])
        df_eng = fe.transform(df_raw)
        
        # Enforce strict feature column order matching the preprocessor list exactly
        num_features = [
            'CPUUsage', 'RAMUsage', 'Temperature', 'Voltage', 'DiskUsage', 'FanSpeed',
            'TemperatureStress', 'VoltageDeviation', 'CombinedLoad', 'ResourcePressureIndex',
            'CoolingEfficiencyProxy', 'FanTemperatureMismatch', 'ThermalLoadRatio', 
            'PowerInstabilityIndex', 'DiskStressIndex',
            'CPU_Temp_Interaction', 'RAM_CPU_Interaction', 'Temp_VoltageDev_Interaction',
            'Temp_FanSpeed_Ratio', 'Disk_CPU_Interaction', 'DegradationSeverityIndex'
        ]
        
        # Ensure imputer is fit-aligned
        preprocessor = self.models.get('problem_preprocessor')
        if df_eng.isnull().any().any():
            num_cols = preprocessor.transformers_[0][2]
            imputer = preprocessor.transformers_[0][1].named_steps['imputer']
            df_eng = df_eng.copy()
            df_eng[num_cols] = imputer.transform(df_eng[num_cols])

        # Prepare raw data in exact feature order before preprocessor transform
        df_eng_ordered = df_eng[num_features]
        X_processed = preprocessor.transform(df_eng_ordered)
        
        # OOD Novelty Detection Check (True OOD vs validation)
        ood_detected = False
        ood_score = 0.0
        ood_warning = None
        
        ood_model = self.models.get('ood_detector')
        ood_scaler = self.models.get('ood_scaler')
        if ood_model and ood_scaler:
            X_ood_scaled = ood_scaler.transform(df_eng_ordered)
            dist = float(ood_model.compute_distance(X_ood_scaled)[0])
            ood_detected = dist > ood_model.threshold_
            ood_score = round(dist, 2)
            if ood_detected:
                ood_warning = f"OOD Warning: Unfamiliar telemetry combination detected (Mahalanobis Distance = {ood_score:.2f} > threshold {ood_model.threshold_:.2f})."

        # 2. Sensor-Based Multiclass Problem Detection
        cls_model = self.models.get('problem_classifier')
        sensor_probs = cls_model.predict_proba(X_processed)[0]
        classes = cls_model.classes_
        
        # Apply calibrated threshold tuning (threshold >= 0.35 for Overheating to improve recall)
        overheat_idx = list(classes).index('Overheating') if 'Overheating' in classes else -1
        if overheat_idx != -1 and sensor_probs[overheat_idx] >= 0.35:
            sensor_pred = 'Overheating'
        else:
            sensor_pred = cls_model.predict(X_processed)[0]
            
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

        # 4. Multimodal Fusion & Conflict/Multi-Fault Detection
        # Standard fallback category
        final_assessment = sensor_pred
        agreement_status = "High Agreement"
        
        # Check if sensor and NLP models disagree
        if sensor_pred.lower().strip() != complaint_pred.lower().strip():
            agreement_status = "Model Disagreement Detected"
            if sensor_conf >= complaint_conf:
                final_assessment = sensor_pred
            else:
                final_assessment = complaint_pred
                
        # Resolve physical overrides & context-aware temperature interpretation
        Temperature = float(pc_row.get("Temperature")) if pc_row.get("Temperature") is not None else None
        Voltage = float(pc_row.get("Voltage")) if pc_row.get("Voltage") is not None else None
        CPUUsage = float(pc_row.get("CPUUsage")) if pc_row.get("CPUUsage") is not None else 0.0
        RAMUsage = float(pc_row.get("RAMUsage")) if pc_row.get("RAMUsage") is not None else 0.0
        FanSpeed = float(pc_row.get("FanSpeed")) if pc_row.get("FanSpeed") is not None else 2500.0
        DiskUsage = float(pc_row.get("DiskUsage")) if pc_row.get("DiskUsage") is not None else 0.0
        
        # Physical Safety Heuristic Override: force Overheating if Temp exceeds critical boundary (>95°C)
        if Temperature is not None and Temperature > 95.0:
            final_assessment = "Overheating"
            sensor_pred = "Overheating"
            agreement_status = "Physical Heuristic Override"
        
        # Determine Temperature evidence levels
        temp_evidence_level = "Normal thermal status"
        if Temperature is not None:
            if Temperature > 110.0:
                temp_evidence_level = "Critical thermal evidence"
            elif Temperature > 95.0:
                temp_evidence_level = "Severe thermal evidence"
            elif Temperature > 85.0:
                temp_evidence_level = "High thermal evidence"
            elif Temperature > 75.0:
                temp_evidence_level = "Elevated thermal evidence"

        # Multi-fault checks (Overheating + Memory Leak + Power Issue)
        detected_faults = []
        if Temperature is not None and Temperature > 95.0:
            detected_faults.append("Critical Overheating Evidence")
        if RAMUsage > 90.0 or "memory" in complaint_text.lower():
            detected_faults.append("Memory Leak Evidence")
        if Voltage is not None and (Voltage < 9.0 or Voltage > 15.0):
            detected_faults.append("Power Issue Evidence")
            
        multi_fault_flag = "Possible Multi-Fault Condition" if len(detected_faults) >= 2 else None

        # 5. Isolation Forest Anomaly Detection
        anom_model = self.models.get('anomaly_detector')
        anom_scaler = self.models.get('anomaly_scaler')
        
        X_anom_raw = df_eng_ordered[anom_scaler.feature_names_in_]
        X_anom_scaled = anom_scaler.transform(X_anom_raw)
        
        anom_label_code = anom_model.predict(X_anom_scaled)[0]
        anomaly_label = "Abnormal" if anom_label_code == -1 else "Normal"
        raw_score = float(anom_model.decision_function(X_anom_scaled)[0])
        normalized_anom_score = 1.0 / (1.0 + np.exp(raw_score * 8.0))

        # 6. Heuristic Health Index & Rule-Based Risk Indicators (Bypass legacy regressors)
        # Temp penalty
        if Temperature is not None and Temperature > 75.0:
            temp_stress = Temperature - 75.0
            temp_penalty = temp_stress * 1.5
            if Temperature > 95.0:
                temp_penalty += (Temperature - 95.0) * 2.0
            temp_penalty = min(60.0, temp_penalty)
        else:
            temp_penalty = 0.0
            
        # Voltage penalty (nominal is 12.0V)
        if Voltage is not None:
            volt_dev = abs(Voltage - 12.0)
            volt_penalty = min(50.0, volt_dev * 15.0)
        else:
            volt_penalty = 0.0
            
        # Load penalty
        load_penalty = 0.0
        if CPUUsage > 85.0:
            load_penalty += (CPUUsage - 85.0) * 0.5
        if RAMUsage > 85.0:
            load_penalty += (RAMUsage - 85.0) * 0.5
        load_penalty = min(15.0, load_penalty)
        
        # Cooling mismatch penalty
        if Temperature is not None and Temperature > 75.0 and FanSpeed < 2000.0:
            cooling_penalty = 20.0
        else:
            cooling_penalty = 0.0
            
        health_score = max(0.0, min(100.0, 100.0 - temp_penalty - volt_penalty - load_penalty - cooling_penalty))
        health_band = RiskService.get_health_band(health_score)

        # 7. Rule-Based Risk Indicator
        temp_risk = min(50.0, (Temperature - 75.0) * 2.0) if (Temperature is not None and Temperature > 75.0) else 0.0
        volt_risk = min(50.0, abs(Voltage - 12.0) * 20.0) if Voltage is not None else 0.0
        load_risk = (CPUUsage * 0.3 + RAMUsage * 0.7) * 0.2
        cooling_risk = 30.0 if (Temperature is not None and Temperature > 80.0 and FanSpeed < 2200.0) else 0.0
        
        failure_risk = max(0.0, min(100.0, temp_risk + volt_risk + load_risk + cooling_risk))

        # 8. Maintenance Urgency & will_fail_soon mapping
        if health_score < 50.0 or failure_risk > 60.0 or (Temperature is not None and Temperature > 105.0) or (Voltage is not None and (Voltage < 8.5 or Voltage > 15.5)):
            risk_level = "Critical"
            will_fail_soon = True
        elif health_score < 70.0 or failure_risk > 40.0 or (Temperature is not None and Temperature > 85.0):
            risk_level = "High"
            will_fail_soon = True
        elif health_score < 85.0 or failure_risk > 20.0:
            risk_level = "Medium"
            will_fail_soon = False
        else:
            risk_level = "Low"
            will_fail_soon = False

        # Calculate operational risk index
        risk_index, _ = RiskService.calculate_risk_index(health_score, failure_risk, normalized_anom_score)

        # 9. Local Explainability
        top_contribs = []
        if explain:
            explainer = self.models.get('explainer')
            top_contribs = explainer.explain_instance(cls_model, X_processed, prediction_type="problem")

        # 10. Trend Forecasting
        forecasting = self.run_forecasting(telemetry_history)

        # Build response features dictionary
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
                "agreement_status": agreement_status,
                "temperature_evidence_level": temp_evidence_level,
                "multi_fault_profile": {
                    "primary": f"Primary: {detected_faults[0]}" if len(detected_faults) > 0 else "Primary: Normal status",
                    "secondary": f"Secondary: {detected_faults[1]}" if len(detected_faults) > 1 else None,
                    "diagnostic_flag": multi_fault_flag
                }
            },
            "predictive_health": {
                "health_score": round(health_score, 1),
                "health_band": health_band,
                "near_term_failure_risk": round(failure_risk, 1),
                "will_fail_soon": will_fail_soon,
                "failure_confidence": round(sensor_conf * 100.0, 2), # mapped to classifier conf
                "remaining_useful_life_days": None, # compatibility mapping
                "risk_index": risk_index,
                "risk_level": risk_level,
                "ood_flag": ood_detected,
                "ood_warning": ood_warning,
                "metadata": {
                    "health_index_formula": "100 - temp_penalty - volt_penalty - load_penalty - cooling_penalty",
                    "risk_indicator_formula": "temp_risk + volt_risk + load_risk + cooling_risk",
                    "version": "1.0-heuristic-safety-layer",
                    "nature": "Deterministic Physical Heuristic Rule",
                    "note": "Exposes rule-based indicators instead of learned supervised predictions to avoid circular target leakage."
                }
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

        history = sorted(telemetry_history, key=lambda x: x.timestamp)
        times = np.array([h.timestamp.timestamp() for h in history]).reshape(-1, 1)
        temps = np.array([h.temperature for h in history])
        volts = np.array([h.voltage for h in history])
        cpus = np.array([h.cpu_usage for h in history])
        
        last_time = history[-1].timestamp
        future_times_dt = [last_time + timedelta(days=1), last_time + timedelta(days=2)]
        future_times_numeric = np.array([dt.timestamp() for dt in future_times_dt]).reshape(-1, 1)
        
        temp_model = LinearRegression().fit(times, temps)
        volt_model = LinearRegression().fit(times, volts)
        cpu_model = LinearRegression().fit(times, cpus)
        
        temp_preds = temp_model.predict(future_times_numeric)
        volt_preds = volt_model.predict(future_times_numeric)
        cpu_preds = cpu_model.predict(future_times_numeric)
        
        temp_forecast = []
        volt_forecast = []
        cpu_forecast = []
        
        for idx, dt in enumerate(future_times_dt):
            temp_forecast.append({"timestamp": dt, "value": round(float(temp_preds[idx]), 3)})
            volt_forecast.append({"timestamp": dt, "value": round(float(volt_preds[idx]), 3)})
            cpu_usage = min(100.0, max(0.0, float(cpu_preds[idx])))
            cpu_forecast.append({"timestamp": dt, "value": round(cpu_usage, 3)})
            
        return {
            "temperature_forecast": temp_forecast,
            "voltage_forecast": volt_forecast,
            "cpu_usage_forecast": cpu_forecast,
            "status": "success"
        }
