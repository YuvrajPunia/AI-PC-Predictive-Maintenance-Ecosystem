import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.services.prediction_service import PredictionService
from backend.app.services.similarity_service import SimilarityService

def run_tests():
    print("==================================================")
    print("RUNNING PARAMETERIZED SANITY TEST SUITE")
    print("==================================================")
    
    ps = PredictionService()
    ss = SimilarityService()
    
    # Check if models are loaded
    assert len(ps.models) > 0, "Failed to load models in PredictionService"
    
    # Mandatory Parameterized Test 1: Original Failure Case (Experiencing overheating at 117°C)
    print("\n[Test 1] Parameterized Overheating at 117°C...")
    pc_row_1 = {
        "PC_ID": "DRDO-PC-0001",
        "ModelName": "HP Z2 G8",
        "Department": "Research",
        "Location": "Lab 1",
        "CPUUsage": 88.0,
        "RAMUsage": 45.0,
        "Temperature": 117.0,
        "Voltage": 12.0,
        "DiskUsage": 55.0,
        "FanSpeed": 3500.0
    }
    complaint_1 = "Experiencing overheating."
    ans_1 = ps.run_inference(pc_row_1, complaint_1)
    
    # Assertions
    pred_prob_1 = ans_1["problem_analysis"]["final_assessment"]
    print(f" -> Predicted Problem: {pred_prob_1}")
    print(f" -> Temperature Evidence Level: {ans_1['problem_analysis']['temperature_evidence_level']}")
    print(f" -> Heuristic Health Index: {ans_1['predictive_health']['health_score']}")
    print(f" -> Rule-Based Risk Indicator: {ans_1['predictive_health']['near_term_failure_risk']}")
    print(f" -> Maintenance Urgency: {ans_1['predictive_health']['risk_level']}")
    
    assert pred_prob_1 == "Overheating", f"Expected Overheating, got {pred_prob_1}"
    assert ans_1["problem_analysis"]["temperature_evidence_level"] == "Critical thermal evidence", "Expected critical thermal evidence descriptor"
    assert ans_1["predictive_health"]["health_score"] < 50.0, "Expected low health score under critical temperature"
    
    # Mandatory Parameterized Test 2: Verify 100% DiskUsage alone does not imply Disk Failure
    print("\n[Test 2] Verifying 100% DiskUsage alone does not imply Disk Failure...")
    # Even if DiskUsage is 100% (which correlated with Disk Failure in raw data)
    pc_row_2 = {
        "PC_ID": "DRDO-PC-0002",
        "ModelName": "Dell Precision 3650",
        "Department": "Finance",
        "Location": "Office 2",
        "CPUUsage": 40.0,
        "RAMUsage": 50.0,
        "Temperature": 50.0,
        "Voltage": 12.0,
        "DiskUsage": 100.0,
        "FanSpeed": 2000.0
    }
    ans_2 = ps.run_inference(pc_row_2, "Disk is getting full.")
    pred_prob_2 = ans_2["problem_analysis"]["sensor_prediction"]
    print(f" -> Sensor Prediction under 100% DiskUsage: {pred_prob_2}")
    assert pred_prob_2 != "Disk Failure", "Error: 100% DiskUsage alone mapped to Disk Failure!"
    print(f" -> DegradationSeverityIndex: {ans_2['engineered_features']['DegradationSeverityIndex']}")
    assert ans_2['engineered_features']['DegradationSeverityIndex'] > 0.0, "Expected elevated resource-pressure warning feature"

    # Mandatory Parameterized Test 3: Verify Disk Failure can still be detected through complaint NLP
    print("\n[Test 3] Verifying Disk Failure detection through NLP...")
    ans_3 = ps.run_inference(pc_row_2, "Repeated IO errors and storage device disconnects.")
    nlp_prob_3 = ans_3["problem_analysis"]["complaint_prediction"]
    fused_prob_3 = ans_3["problem_analysis"]["final_assessment"]
    print(f" -> NLP Prediction: {nlp_prob_3}")
    print(f" -> Fused Final Assessment: {fused_prob_3}")
    assert nlp_prob_3 == "Disk Failure", f"Expected NLP to predict Disk Failure, got {nlp_prob_3}"
    assert fused_prob_3 == "Disk Failure", f"Expected fused to be Disk Failure, got {fused_prob_3}"

    # Mandatory Parameterized Test 4: Verify True OOD flagging on joint anomalies
    print("\n[Test 4] Verifying True OOD joint-anomaly detection...")
    pc_row_4 = {
        "PC_ID": "DRDO-PC-0004",
        "ModelName": "HP Z2 G8",
        "Department": "Research",
        "Location": "Lab 1",
        "CPUUsage": 100.0,
        "RAMUsage": 100.0,
        "Temperature": 20.0,
        "Voltage": 12.0,
        "DiskUsage": 50.0,
        "FanSpeed": 0.0
    }
    ans_4 = ps.run_inference(pc_row_4, "PC is running slow.")
    print(f" -> OOD Flag: {ans_4['predictive_health']['ood_flag']}")
    print(f" -> OOD Warning: {ans_4['predictive_health']['ood_warning']}")
    assert ans_4["predictive_health"]["ood_flag"] is True, "Expected OOD flag to be True for joint anomaly combination"

    # Mandatory Parameterized Test 5: Verify weak historical matches (like 15%) are suppressed
    print("\n[Test 5] Verifying weak historical matches suppression...")
    # Query with a completely unrelated text complaint
    similar_cases = ss.retrieve_similar_cases(
        query_complaint="The keyboard keycaps are sticking and spacebar is loose.",
        predicted_problem="No Problem",
        pc_model="HP Z2 G8",
        query_symptoms="",
        top_k=3
    )
    print(f" -> Number of retrieved cases for unrelated query: {len(similar_cases)}")
    for case in similar_cases:
        print(f"    - Match: {case['repair_id']} (Score: {case['similarity_score']})")
        assert case['similarity_score'] >= 40.0, "Retrieved case is below threshold!"
    assert len(similar_cases) == 0, f"Expected 0 matches for unrelated query, got {len(similar_cases)}"

    # Mandatory Parameterized Test 6: Verify progressive temperature evidence levels
    print("\n[Test 6] Verifying progressive temperature evidence...")
    temps_to_test = [45.0, 80.0, 90.0, 100.0, 117.0]
    expected_evidence = [
        "Normal thermal status",
        "Elevated thermal evidence",
        "High thermal evidence",
        "Severe thermal evidence",
        "Critical thermal evidence"
    ]
    for temp, exp_ev in zip(temps_to_test, expected_evidence):
        pc_row = pc_row_1.copy()
        pc_row["Temperature"] = temp
        ans = ps.run_inference(pc_row, "Auditing thermals.")
        actual_ev = ans["problem_analysis"]["temperature_evidence_level"]
        print(f"    - Temp {temp}°C -> {actual_ev}")
        assert actual_ev == exp_ev, f"Expected '{exp_ev}', got '{actual_ev}'"

    # Mandatory Parameterized Test 7: Multi-fault output diagnostic validation
    print("\n[Test 7] Verifying multi-fault diagnostic output profile...")
    pc_row_7 = {
        "PC_ID": "DRDO-PC-0007",
        "ModelName": "HP Z2 G8",
        "Department": "Research",
        "Location": "Lab 1",
        "CPUUsage": 80.0,
        "RAMUsage": 97.0,
        "Temperature": 117.0,
        "Voltage": 12.0,
        "DiskUsage": 50.0,
        "FanSpeed": 3000.0
    }
    ans_7 = ps.run_inference(pc_row_7, "Progressive memory growth and throttling.")
    profile = ans_7["problem_analysis"]["multi_fault_profile"]
    print(f" -> Primary: {profile['primary']}")
    print(f" -> Secondary: {profile['secondary']}")
    print(f" -> Flag: {profile['diagnostic_flag']}")
    
    assert profile["diagnostic_flag"] == "Possible Multi-Fault Condition", "Expected multi-fault condition flag"
    assert "Critical Overheating" in profile["primary"], "Expected primary to be Overheating"
    assert "Memory Leak" in profile["secondary"], "Expected secondary to be Memory Leak"

    print("\n==================================================")
    print("ALL SANITY TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
