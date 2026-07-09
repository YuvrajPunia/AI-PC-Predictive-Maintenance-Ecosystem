import urllib.request
import urllib.error
import json

def run_production_tests():
    print("==================================================")
    print("RUNNING LIVE PRODUCTION API TESTS")
    print("==================================================")
    
    base_url = "https://ai-pc-predictive-maintenance-ecosystem.onrender.com"
    
    # 1. Test PC fleet listing
    print("\n[Prod Check 1] GET /api/pcs...")
    try:
        req = urllib.request.Request(f"{base_url}/api/pcs", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            print(f" -> Status: {res.status} OK")
            print(f" -> Current Fleet Size: {len(data)}")
    except Exception as e:
        print(f" -> Failed: {e}")
        return

    # 2. Register New PC (HP Z2 G9)
    print("\n[Prod Check 2] POST /api/pcs (Register PC)...")
    pc_id = "DRDO-PC-9999"
    payload = {
        "model_name": "HP Z2 G9",
        "department": "Security Systems",
        "location": "Block-B Floor-3",
        "cpu_usage": 15.0,
        "ram_usage": 20.0,
        "temperature": 45.0,
        "voltage": 12.0,
        "disk_usage": 30.0,
        "fan_speed": 2200.0
    }
    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"{base_url}/api/pcs/",
        data=req_data,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as res:
            res_body = json.loads(res.read().decode('utf-8'))
            pc_id = res_body.get("pc_id", pc_id)
            print(f" -> Status: {res.status} OK")
            print(f" -> Registered PC ID: {pc_id}")
    except urllib.error.HTTPError as he:
        print(f" -> Failed with HTTP {he.code}: {he.read().decode('utf-8')}")
        return
    except Exception as e:
        print(f" -> Failed: {e}")
        return

    # 3. Test Overheating Case
    print("\n[Prod Check 3] POST /api/analyze (Overheating Test Case)...")
    payload_overheat = {
        "pc_id": pc_id,
        "complaint": "Experiencing overheating.",
        "current_readings": {
            "temperature": 120.0,
            "fan_speed": 3200.0,
            "cpu_usage": 50.0,
            "ram_usage": 50.0,
            "voltage": 15.0,
            "disk_usage": 50.0
        }
    }
    req_data = json.dumps(payload_overheat).encode('utf-8')
    req = urllib.request.Request(
        f"{base_url}/api/analyze",
        data=req_data,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as res:
            res_body = json.loads(res.read().decode('utf-8'))
            print(f" -> Status: {res.status} OK")
            print(f" -> Primary Diagnosis: {res_body['problem_analysis']['final_assessment']}")
            print(f" -> Heuristic Health Index: {res_body['predictive_health']['health_score']}%")
            print(f" -> Rule-Based Risk Indicator: {res_body['predictive_health']['near_term_failure_risk']}%")
            print(f" -> Maintenance Urgency: {res_body['predictive_health']['risk_level']}")
            print(" -> Top 3 Similar Cases:")
            for sc in res_body['similar_cases']:
                print(f"    * Rank {sc['rank']}: {sc['repair_id']} ({sc['similarity_score']}% Match - {sc['match_strength']})")
    except Exception as e:
        print(f" -> Failed: {e}")

    # 4. Test Memory Leak Case
    print("\n[Prod Check 4] POST /api/analyze (Memory Leak Test Case)...")
    payload_mem = {
        "pc_id": pc_id,
        "complaint": "Memory usage keeps increasing over time. The system becomes very slow and applications freeze after prolonged use.",
        "current_readings": {
            "temperature": 58.0,
            "fan_speed": 2800.0,
            "cpu_usage": 45.0,
            "ram_usage": 96.0,
            "voltage": 12.0,
            "disk_usage": 55.0
        }
    }
    req_data = json.dumps(payload_mem).encode('utf-8')
    req = urllib.request.Request(
        f"{base_url}/api/analyze",
        data=req_data,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as res:
            res_body = json.loads(res.read().decode('utf-8'))
            print(f" -> Status: {res.status} OK")
            print(f" -> Primary Diagnosis: {res_body['problem_analysis']['final_assessment']}")
            print(f" -> Heuristic Health Index: {res_body['predictive_health']['health_score']}%")
            print(f" -> Rule-Based Risk Indicator: {res_body['predictive_health']['near_term_failure_risk']}%")
            print(f" -> Maintenance Urgency: {res_body['predictive_health']['risk_level']}")
            print(" -> Top 3 Similar Cases:")
            for sc in res_body['similar_cases']:
                print(f"    * Rank {sc['rank']}: {sc['repair_id']} ({sc['similarity_score']}% Match - {sc['match_strength']})")
    except Exception as e:
        print(f" -> Failed: {e}")

if __name__ == "__main__":
    run_production_tests()
