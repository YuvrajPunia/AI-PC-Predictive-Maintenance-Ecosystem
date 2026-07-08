from backend.app.config import TEMP_WARNING_THRESHOLD, VOLTAGE_NOMINAL

class RiskService:
    @staticmethod
    def get_health_band(score: float) -> str:
        """Translates health score (0-100) into a qualitative band."""
        if score >= 80.0:
            return "Healthy"
        elif score >= 60.0:
            return "Moderate"
        elif score >= 40.0:
            return "Poor"
        else:
            return "Critical"

    @staticmethod
    def get_risk_level(risk_index: float) -> str:
        """Translates risk index (0-100) into operational risk level bands."""
        if risk_index < 35.0:
            return "Low"
        elif risk_index < 60.0:
            return "Medium"
        elif risk_index < 80.0:
            return "High"
        else:
            return "Critical"

    @classmethod
    def calculate_risk_index(cls, health_score: float, failure_prob: float, anomaly_score: float) -> tuple:
        """
        Calculates operational risk index using the weighted formula:
        RiskIndex = 0.35 * FailureProbability + 0.30 * AnomalyScore * 100 + 0.35 * (100 - HealthScore)
        Returns: (risk_index, risk_level)
        """
        # Ensure failure probability is on 0-100 scale (or multiply if 0-1)
        if failure_prob <= 1.0:
            failure_prob = failure_prob * 100.0
            
        # Ensure anomaly score is 0-100
        anom_term = anomaly_score * 100.0 if anomaly_score <= 1.0 else anomaly_score
        
        health_term = 100.0 - health_score
        
        risk_index = (0.35 * failure_prob) + (0.30 * anom_term) + (0.35 * health_term)
        risk_index = min(100.0, max(0.0, risk_index))
        
        return round(risk_index, 2), cls.get_risk_level(risk_index)
