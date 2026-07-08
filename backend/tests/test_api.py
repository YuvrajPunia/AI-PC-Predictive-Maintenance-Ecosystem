import pytest
from fastapi.testclient import TestClient
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.main import app
from backend.app.config import REPAIR_CSV_PATH

client = TestClient(app)

def test_health_check_api():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["Healthy", "Degraded"]

def test_pcs_list_api():
    response = client.get("/api/pcs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "pc_id" in data[0]
        assert "model_name" in data[0]
        assert "temperature" in data[0]

def test_analyze_complaint_api():
    # Perform analysis
    payload = {
        "pc_id": "DRDO-PC-0001",
        "complaint": "My laptop screen gets freezing and RAM usage is near 95% constant."
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "analysis_id" in data
    assert "current_sensors" in data
    assert "problem_analysis" in data
    assert "predictive_health" in data
    assert "similar_cases" in data
    assert "recommendation" in data
    
    # Assert top-3 limits
    assert len(data["similar_cases"]) <= 3

def test_complete_repair_api():
    # Perform completion transaction
    payload = {
        "pc_id": "DRDO-PC-0002",
        "original_complaint": "Screen froze during work",
        "symptoms": "Hangs frequently, high CPU load",
        "problem_detected": "Memory Leak",
        "confirmed_diagnosis": "System monitoring service memory leak",
        "root_cause": "Telemetry script socket buffer leak",
        "treatment_taken": "Updated custom agent to v1.2",
        "downtime_minutes": 45,
        "technician_notes": "Test verification ok"
    }
    
    response = client.post("/api/repairs/complete", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "repair_id" in data
    assert data["pc_id"] == "DRDO-PC-0002"
    assert data["problem_detected"] == "Memory Leak"
    assert data["confirmed_diagnosis"] == "System monitoring service memory leak"
