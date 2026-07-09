import urllib.request
import urllib.error
import json

def verify():
    print("==================================================")
    print("VERIFYING LOCAL FASTAPI API ENDPOINTS")
    print("==================================================")

    base_url = "http://localhost:8000"

    # 1. Test Root/Docs (Health check)
    print("\n[API Check 1] GET /docs (Health Check)...")
    try:
        req = urllib.request.Request(f"{base_url}/docs")
        with urllib.request.urlopen(req) as response:
            status = response.status
            print(f" -> Status: {status} OK")
    except Exception as e:
        print(f" -> Failed: {e}")

    # 2. Test Overview endpoint
    print("\n[API Check 2] GET /api/dashboard/overview...")
    try:
        req = urllib.request.Request(f"{base_url}/api/dashboard/overview")
        with urllib.request.urlopen(req) as response:
            status = response.status
            data = json.loads(response.read().decode('utf-8'))
            print(f" -> Status: {status} OK")
            stats = data.get('stats', {})
            print(f" -> Fleet Average Health: {stats.get('average_health_score')}%")
            print(f" -> Active Anomalies: {stats.get('abnormal_pcs')}")
            print(f" -> High/Critical Risk Systems: {stats.get('high_risk_pcs')}")
    except Exception as e:
        print(f" -> Failed: {e}")

    # 3. Test PC Fleet endpoint
    print("\n[API Check 3] GET /api/pcs...")
    try:
        req = urllib.request.Request(f"{base_url}/api/pcs")
        with urllib.request.urlopen(req) as response:
            status = response.status
            data = json.loads(response.read().decode('utf-8'))
            print(f" -> Status: {status} OK")
            print(f" -> Loaded PCs Count: {len(data)}")
    except Exception as e:
        print(f" -> Failed: {e}")

    # 4. Test Repair History endpoint
    print("\n[API Check 4] GET /api/repairs...")
    try:
        req = urllib.request.Request(f"{base_url}/api/repairs")
        with urllib.request.urlopen(req) as response:
            status = response.status
            data = json.loads(response.read().decode('utf-8'))
            print(f" -> Status: {status} OK")
            print(f" -> Historical Repairs Count: {len(data)}")
    except Exception as e:
        print(f" -> Failed: {e}")

    # 5. Test AI Analysis Post (Manual Overheating Override)
    print("\n[API Check 5] POST /api/analyze (117°C Overheating Overrides)...")
    payload = {
        "pc_id": "DRDO-PC-0003",
        "complaint": "Experiencing overheating.",
        "current_readings": {
            "temperature": 117.0,
            "fan_speed": 3200.0,
            "cpu_usage": 50.0,
            "ram_usage": 50.0,
            "voltage": 15.0,
            "disk_usage": 50.0
        }
    }
    
    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"{base_url}/api/analyze",
        data=req_data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            res_body = json.loads(response.read().decode('utf-8'))
            print(f" -> Status: {status} OK")
            print("\nAnalysis Result Details:")
            print(f"  - Primary Diagnosis: {res_body['problem_analysis']['final_assessment']}")
            print(f"  - Multi-fault Output Profile:")
            print(json.dumps(res_body['problem_analysis']['multi_fault_profile'], indent=4))
            print(f"  - Inferred/Used Sensor Inputs:")
            print(json.dumps(res_body['current_sensors'], indent=4))
            print(f"  - Heuristic Health Index: {res_body['predictive_health']['health_score']}%")
            print(f"  - Rule-Based Risk Indicator: {res_body['predictive_health']['near_term_failure_risk']}%")
            print(f"  - Maintenance Urgency: {res_body['predictive_health']['risk_level']}")
            print(f"  - Anomaly Flag: {res_body['anomaly']['label']} (Score: {res_body['anomaly']['score']})")
            print(f"  - OOD Flag: {res_body['predictive_health']['ood_flag']}")
            if 'ood_warning' in res_body['predictive_health']:
                print(f"  - OOD Warning: {res_body['predictive_health']['ood_warning']}")
            
            # Print features to look for DegradationSeverityIndex
            eng_feats = res_body.get('engineered_features', {})
            print(f"  - DegradationSeverityIndex: {eng_feats.get('DegradationSeverityIndex', 'N/A')}")
    except urllib.error.HTTPError as he:
        print(f" -> HTTP Error {he.code}: {he.read().decode('utf-8')}")
    except Exception as e:
        print(f" -> Failed: {e}")

if __name__ == "__main__":
    verify()
