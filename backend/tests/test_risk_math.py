import pytest
from backend.app.services.risk_service import RiskService

def test_health_band_mapping():
    assert RiskService.get_health_band(95.0) == "Healthy"
    assert RiskService.get_health_band(80.0) == "Healthy"
    assert RiskService.get_health_band(75.0) == "Moderate"
    assert RiskService.get_health_band(60.0) == "Moderate"
    assert RiskService.get_health_band(55.0) == "Poor"
    assert RiskService.get_health_band(40.0) == "Poor"
    assert RiskService.get_health_band(30.0) == "Critical"
    assert RiskService.get_health_band(0.0) == "Critical"

def test_risk_level_mapping():
    assert RiskService.get_risk_level(10.0) == "Low"
    assert RiskService.get_risk_level(34.9) == "Low"
    assert RiskService.get_risk_level(35.0) == "Medium"
    assert RiskService.get_risk_level(59.9) == "Medium"
    assert RiskService.get_risk_level(60.0) == "High"
    assert RiskService.get_risk_level(79.9) == "High"
    assert RiskService.get_risk_level(80.0) == "Critical"
    assert RiskService.get_risk_level(95.0) == "Critical"

def test_risk_index_calculation():
    # Test case 1: Fully healthy (Health=100, FailureProb=0, AnomalyScore=0) -> Risk=0 (Low)
    idx, level = RiskService.calculate_risk_index(100.0, 0.0, 0.0)
    assert idx == 0.0
    assert level == "Low"

    # Test case 2: Stressed metrics (Health=50, FailureProb=50, AnomalyScore=0.5)
    # RiskIndex = 0.35 * 50 + 0.30 * 50 + 0.35 * 50 = 17.5 + 15 + 17.5 = 50.0 (Medium)
    idx, level = RiskService.calculate_risk_index(50.0, 50.0, 0.5)
    assert idx == 50.0
    assert level == "Medium"

    # Test case 3: Extreme failure risk (Health=20, FailureProb=80, AnomalyScore=0.9)
    # RiskIndex = 0.35 * 80 + 0.30 * 90 + 0.35 * 80 = 28 + 27 + 28 = 83.0 (Critical)
    idx, level = RiskService.calculate_risk_index(20.0, 80.0, 0.9)
    assert idx == 83.0
    assert level == "Critical"
