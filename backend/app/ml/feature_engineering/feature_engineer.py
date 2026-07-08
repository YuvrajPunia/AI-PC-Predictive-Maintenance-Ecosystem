import pandas as pd
import numpy as np
import os
import joblib
from backend.app.config import TEMP_WARNING_THRESHOLD, VOLTAGE_NOMINAL, MODELS_DIR

class FeatureEngineer:
    def __init__(self):
        self.fitted_baselines = {}
        self.is_fit = False

    def fit(self, df: pd.DataFrame):
        """Fits baseline statistics from the training set to prevent data leakage."""
        self.fitted_baselines['median_voltage'] = float(df['Voltage'].median()) if 'Voltage' in df.columns else VOLTAGE_NOMINAL
        self.fitted_baselines['median_temp'] = float(df['Temperature'].median()) if 'Temperature' in df.columns else 50.0
        self.fitted_baselines['median_fanspeed'] = float(df['FanSpeed'].median()) if 'FanSpeed' in df.columns else 2500.0
        self.is_fit = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforms input DataFrame by adding engineered degradation and interaction features."""
        df_copy = df.copy()
        
        # 1. Temperature Stress
        df_copy['TemperatureStress'] = (df_copy['Temperature'] - TEMP_WARNING_THRESHOLD).clip(lower=0.0)
        
        # 2. Voltage Deviation
        med_volt = self.fitted_baselines.get('median_voltage', VOLTAGE_NOMINAL)
        df_copy['VoltageDeviation'] = (df_copy['Voltage'] - med_volt).abs()
        
        # 3. CPU-RAM Combined Load
        df_copy['CombinedLoad'] = (df_copy['CPUUsage'] * 0.6) + (df_copy['RAMUsage'] * 0.4)
        
        # 4. Resource Pressure Index
        df_copy['ResourcePressureIndex'] = (df_copy['CPUUsage'] + df_copy['RAMUsage'] + df_copy['DiskUsage']) / 3.0
        
        # 5. Cooling Efficiency Proxy
        df_copy['CoolingEfficiencyProxy'] = df_copy['FanSpeed'] / (df_copy['Temperature'] + 1.0)
        
        # 6. Fan-Temperature Mismatch
        # Elevated temperature (>75°C) combined with low fan speed (<2000 RPM)
        df_copy['FanTemperatureMismatch'] = np.where(
            (df_copy['Temperature'] > TEMP_WARNING_THRESHOLD) & (df_copy['FanSpeed'] < 2000.0),
            (df_copy['Temperature'] - TEMP_WARNING_THRESHOLD) * (2000.0 - df_copy['FanSpeed']) / 1000.0,
            0.0
        )
        
        # 7. Thermal Load Ratio
        df_copy['ThermalLoadRatio'] = df_copy['Temperature'] / (df_copy['CPUUsage'] + 1.0)
        
        # 8. Power Instability Index
        df_copy['PowerInstabilityIndex'] = df_copy['VoltageDeviation'] * (df_copy['CPUUsage'] / 50.0)
        
        # 9. Disk Stress Index
        df_copy['DiskStressIndex'] = df_copy['DiskUsage'] * (df_copy['RAMUsage'] / 50.0)
        
        # 10. Sensor Interactions
        df_copy['CPU_Temp_Interaction'] = df_copy['CPUUsage'] * df_copy['Temperature']
        df_copy['RAM_CPU_Interaction'] = df_copy['RAMUsage'] * df_copy['CPUUsage']
        df_copy['Temp_VoltageDev_Interaction'] = df_copy['Temperature'] * df_copy['VoltageDeviation']
        df_copy['Temp_FanSpeed_Ratio'] = df_copy['Temperature'] / (df_copy['FanSpeed'] + 1.0)
        df_copy['Disk_CPU_Interaction'] = df_copy['DiskUsage'] * df_copy['CPUUsage']
        
        # 11. Degradation Severity Index (Weighted sum of key stress factors)
        df_copy['DegradationSeverityIndex'] = (
            df_copy['TemperatureStress'] * 1.5 +
            df_copy['VoltageDeviation'] * 10.0 +
            df_copy['FanTemperatureMismatch'] * 2.0 +
            (df_copy['CPUUsage'] > 85.0).astype(float) * 10.0 +
            (df_copy['RAMUsage'] > 85.0).astype(float) * 10.0 +
            (df_copy['DiskUsage'] > 90.0).astype(float) * 8.0
        )
        
        return df_copy

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    def generate_engineered_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates deterministic, documented engineered targets:
        - HealthScore (0 to 100)
        - NearTermFailureRisk (0 to 100)
        - WillFailSoon (0 or 1)
        - RemainingUsefulLifeDays (1 to 365)
        """
        df_copy = df.copy()
        
        # --- A. Health Score (0-100) ---
        health = np.ones(len(df_copy)) * 100.0
        
        # Penalize for temperature stress
        temp_penalty = np.where(df_copy['Temperature'] > 75.0, (df_copy['Temperature'] - 75.0) * 1.5, 0.0)
        
        # Penalize for voltage deviation (nominal is 15V. If outside 12-18, subtract 8 per Volt)
        volt_penalty = np.where(df_copy['Voltage'] < 12.0, (12.0 - df_copy['Voltage']) * 8.0, 0.0) + \
                       np.where(df_copy['Voltage'] > 18.0, (df_copy['Voltage'] - 18.0) * 8.0, 0.0)
                       
        # High CPU/RAM load penalty under thermal pressure
        high_load = (df_copy['CPUUsage'] > 85.0) & (df_copy['RAMUsage'] > 85.0)
        load_penalty = np.where(high_load, 15.0, 0.0)
        
        # Cooling failure penalty (fan temp mismatch)
        cooling_penalty = df_copy['FanTemperatureMismatch'] * 1.2
        
        # ProblemDetected penalty (for training problem alignment)
        problem_penalties = {
            'No Problem': 0.0,
            'Overheating': 20.0,
            'Disk Failure': 25.0,
            'Memory Leak': 15.0,
            'Power Issue': 30.0
        }
        prob_label = df_copy['ProblemDetected'] if 'ProblemDetected' in df_copy.columns else pd.Series(['No Problem'] * len(df_copy))
        label_penalty = prob_label.map(problem_penalties).fillna(0.0).values
        
        health = health - temp_penalty - volt_penalty - load_penalty - cooling_penalty - label_penalty
        df_copy['HealthScore'] = np.clip(health, 0.0, 100.0)
        
        # --- B. Near-Term Failure Risk (0-100) ---
        # Starts from 0%, rises with stress
        failure_risk = (
            df_copy['TemperatureStress'] * 2.0 +
            df_copy['VoltageDeviation'] * 15.0 +
            df_copy['FanTemperatureMismatch'] * 3.0 +
            np.where(df_copy['CPUUsage'] > 90.0, 15.0, 0.0) +
            np.where(df_copy['RAMUsage'] > 90.0, 15.0, 0.0) +
            np.where(df_copy['DiskUsage'] > 92.0, 10.0, 0.0)
        )
        # Add classification penalty to align it
        class_risk_penalties = {
            'No Problem': 0.0,
            'Overheating': 25.0,
            'Disk Failure': 30.0,
            'Memory Leak': 15.0,
            'Power Issue': 35.0
        }
        label_risk = prob_label.map(class_risk_penalties).fillna(0.0).values
        failure_risk = failure_risk + label_risk
        df_copy['FailureProbability'] = np.clip(failure_risk, 0.0, 100.0)
        
        # --- C. Will Fail Soon (Binary classification target) ---
        # Failed if health is critical (< 50) or risk is high (> 60)
        df_copy['WillFailSoon'] = np.where((df_copy['HealthScore'] < 50.0) | (df_copy['FailureProbability'] > 60.0), 1, 0)
        
        # --- D. Remaining Useful Life Days (1-365) ---
        # Highly degradation-dependent
        base_rul = 365.0
        # Reduce RUL based on health score (non-linear drop)
        health_factor = (df_copy['HealthScore'] / 100.0) ** 1.5
        rul = base_rul * health_factor
        
        # Subtract additional penalty for high volatility
        rul_penalty = (
            df_copy['VoltageDeviation'] * 10.0 +
            df_copy['TemperatureStress'] * 2.0 +
            df_copy['FanTemperatureMismatch'] * 4.0
        )
        rul = rul - rul_penalty
        df_copy['RemainingUsefulLifeDays'] = np.clip(rul, 1.0, 365.0).astype(int)
        
        return df_copy

    def save(self, folder_path: str):
        """Saves fitted feature engineer object."""
        os.makedirs(folder_path, exist_ok=True)
        joblib.dump(self, os.path.join(folder_path, 'feature_engineer.pkl'))
        print("Feature engineer state saved successfully.")
