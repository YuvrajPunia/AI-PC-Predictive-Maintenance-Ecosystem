from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from datetime import datetime
from backend.app.database import get_db
from backend.app.models.schemas import AnalysisRequest, AnalysisResponse, PCBase
from backend.app.models.database_models import Complaint, AnalysisResult
from backend.app.services.pc_service import PCService
from backend.app.services.prediction_service import PredictionService
from backend.app.services.similarity_service import SimilarityService
from backend.app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/analyze", tags=["AI Analysis"])
prediction_service = PredictionService()
similarity_service = SimilarityService()

@router.post("", response_model=AnalysisResponse)
def analyze_complaint(request: AnalysisRequest, db: Session = Depends(get_db)):
    """
    Runs the complete AI/ML diagnostic pipeline on a PC user complaint.
    1. Loads current PC state and historical telemetry.
    2. Resolves effective sensor readings from stored values and optional manual overrides.
    3. Runs feature engineering and model prediction suite (Problem, Anomaly, Health, Failure, RUL).
    4. Retrieves top 3 similar historical completed repairs.
    5. Generates a new evidence-based recommendation.
    6. Saves records to the SQLite database.
    """
    # 1. Fetch PC from database
    pc = PCService.get_pc_by_id(db, request.pc_id)
    if not pc:
        raise HTTPException(status_code=404, detail=f"PC with ID '{request.pc_id}' not found in organization fleet.")
        
    if not request.complaint or not request.complaint.strip():
        raise HTTPException(status_code=400, detail="User complaint text cannot be empty.")

    # 2. Get telemetry history (for forecasting)
    telemetry_history = PCService.get_telemetry_history(db, pc.pc_id, limit=20)

    # 3. Create active Complaint record
    db_complaint = Complaint(
        pc_id=pc.pc_id,
        complaint_text=request.complaint,
        inferred_symptoms="", # Will be set during prediction if parsed
        created_at=datetime.utcnow(),
        status="Pending"
    )
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)

    # 4. Resolve effective sensor readings & validate overrides
    effective_sensors = {}
    sensor_sources = {}
    warnings = []
    
    sensor_fields = ["cpu_usage", "ram_usage", "temperature", "voltage", "disk_usage", "fan_speed"]
    
    for s in sensor_fields:
        manual_val = None
        if request.current_readings:
            manual_val = getattr(request.current_readings, s, None)
            
        if manual_val is not None:
            # Bounds validation
            if s in ["cpu_usage", "ram_usage", "disk_usage"] and not (0 <= manual_val <= 100):
                raise HTTPException(status_code=400, detail=f"Invalid manual {s}: must be between 0 and 100")
            if s == "temperature" and not (-20 <= manual_val <= 150):
                raise HTTPException(status_code=400, detail=f"Invalid manual temperature: must be between -20 and 150 °C")
            if s == "fan_speed" and manual_val < 0:
                raise HTTPException(status_code=400, detail=f"Invalid manual fan speed: cannot be negative")
            if s == "voltage" and not (0 < manual_val <= 30):
                raise HTTPException(status_code=400, detail=f"Invalid manual voltage: must be positive and <= 30V")
                
            effective_sensors[s] = float(manual_val)
            sensor_sources[s] = {"value": float(manual_val), "source": "manual"}
        else:
            stored_val = getattr(pc, s, None)
            if stored_val is not None:
                effective_sensors[s] = float(stored_val)
                sensor_sources[s] = {"value": float(stored_val), "source": "stored"}
            else:
                effective_sensors[s] = None
                sensor_sources[s] = {"value": None, "source": "unavailable"}

    available_sensors_count = sum(1 for v in effective_sensors.values() if v is not None)
    
    if available_sensors_count == 0:
        # All-telemetry missing fallback (NLP-only)
        warnings.append("All sensor readings are unavailable. Sensor-based AI analysis was skipped.")
        
        # Predict complaint category only
        complaint_pred = "No Problem"
        complaint_conf = 1.0
        nlp_vectorizer = prediction_service.models.get('complaint_vectorizer')
        nlp_cls = prediction_service.models.get('complaint_classifier')
        
        if nlp_vectorizer and nlp_cls:
            X_text = nlp_vectorizer.transform([request.complaint])
            complaint_pred = nlp_cls.predict(X_text)[0]
            nlp_probs = nlp_cls.predict_proba(X_text)[0]
            nlp_classes = nlp_cls.classes_
            complaint_conf = float(nlp_probs[list(nlp_classes).index(complaint_pred)])
            
        fused_problem = complaint_pred
        agreement_status = "No Telemetry Available - Complaint NLP Only"
        
        analysis = {
            "engineered_features": {},
            "problem_analysis": {
                "sensor_prediction": None,
                "sensor_confidence": None,
                "complaint_prediction": complaint_pred,
                "complaint_confidence": round(complaint_conf * 100.0, 2),
                "final_assessment": fused_problem,
                "agreement_status": agreement_status
            },
            "predictive_health": {
                "health_score": None,
                "health_band": None,
                "near_term_failure_risk": None,
                "will_fail_soon": None,
                "failure_confidence": None,
                "remaining_useful_life_days": None,
                "risk_index": None,
                "risk_level": "Unavailable"
            },
            "anomaly": {
                "label": None,
                "score": None
            },
            "explainability": {
                "method": "N/A",
                "top_contributing_features": []
            },
            "forecasting": {
                "temperature_forecast": None,
                "voltage_forecast": None,
                "cpu_usage_forecast": None,
                "status": "unavailable"
            }
        }
        
        anomaly_label = None
        anomaly_score = None
        health_score = None
        failure_risk = None
        rul_days = None
        risk_level = "Unavailable"
        risk_index = None
    else:
        # Check if partial telemetry triggers warning
        if available_sensors_count < 6:
            warnings.append("Some predictive outputs used training-pipeline imputation because current telemetry was incomplete.")
            
        # Run full ML Models pipeline
        pc_row = {
            "PC_ID": pc.pc_id,
            "ModelName": pc.model_name,
            "Department": pc.department,
            "Location": pc.location,
            "CPUUsage": effective_sensors["cpu_usage"],
            "RAMUsage": effective_sensors["ram_usage"],
            "Temperature": effective_sensors["temperature"],
            "Voltage": effective_sensors["voltage"],
            "DiskUsage": effective_sensors["disk_usage"],
            "FanSpeed": effective_sensors["fan_speed"],
            "LastUpdated": pc.last_updated.isoformat()
        }
        
        analysis = prediction_service.run_inference(
            pc_row=pc_row,
            complaint_text=request.complaint,
            telemetry_history=telemetry_history
        )
        
        fused_problem = analysis["problem_analysis"]["final_assessment"]
        health_score = analysis["predictive_health"]["health_score"]
        failure_risk = analysis["predictive_health"]["near_term_failure_risk"]
        rul_days = analysis["predictive_health"]["remaining_useful_life_days"]
        anomaly_label = analysis["anomaly"]["label"]
        anomaly_score = analysis["anomaly"]["score"]
        risk_index = analysis["predictive_health"]["risk_index"]
        risk_level = analysis["predictive_health"]["risk_level"]

    # 5. Retrieve top 3 similar completed repairs
    similar_cases = similarity_service.retrieve_similar_cases(
        query_complaint=request.complaint,
        predicted_problem=fused_problem or "No Problem",
        pc_model=pc.model_name,
        query_symptoms="",  # Removed duplicate passing of request.complaint
        top_k=3,
        upstream_confidence=(analysis["problem_analysis"]["sensor_confidence"] / 100.0) if (analysis and "problem_analysis" in analysis and analysis["problem_analysis"]["sensor_confidence"] is not None) else 1.0,
        model_disagreement=(analysis["problem_analysis"]["agreement_status"] == "Model Disagreement Detected") if (analysis and "problem_analysis" in analysis) else False
    )
    
    # Update complaint's inferred symptoms if any matches
    if similar_cases:
        db_complaint.inferred_symptoms = similar_cases[0]["symptoms"]
        db.commit()
        if all(float(c.get("similarity_score", 0.0)) < 70.0 for c in similar_cases):
            warnings.append("No strong historical analogue found. Showing the nearest available historical cases for contextual reference.")

    # 6. Generate structured AI Recommendation
    recommendation = RecommendationService.generate_recommendation(
        pc_id=pc.pc_id,
        complaint=request.complaint,
        fused_problem=fused_problem or "No Problem",
        health_score=health_score if health_score is not None else 100.0,
        failure_risk=failure_risk if failure_risk is not None else 0.0,
        rul_days=rul_days if rul_days is not None else 365,
        anomaly_label=anomaly_label or "Normal",
        sensors={
            "cpu_usage": effective_sensors["cpu_usage"] if effective_sensors["cpu_usage"] is not None else 0.0,
            "ram_usage": effective_sensors["ram_usage"] if effective_sensors["ram_usage"] is not None else 0.0,
            "temperature": effective_sensors["temperature"] if effective_sensors["temperature"] is not None else 45.0,
            "voltage": effective_sensors["voltage"] if effective_sensors["voltage"] is not None else 15.0,
            "disk_usage": effective_sensors["disk_usage"] if effective_sensors["disk_usage"] is not None else 0.0,
            "fan_speed": effective_sensors["fan_speed"] if effective_sensors["fan_speed"] is not None else 2500.0
        },
        engineered_features=analysis["engineered_features"],
        similar_cases=similar_cases
    )

    # 7. Save Analysis Results to Database for Audit logs
    analysis_id = f"ANL-{db_complaint.complaint_id:05d}"
    db_analysis = AnalysisResult(
        analysis_id=analysis_id,
        complaint_id=db_complaint.complaint_id,
        pc_id=pc.pc_id,
        predicted_problem=fused_problem,
        prediction_confidence=analysis["problem_analysis"]["sensor_confidence"],
        anomaly_label=anomaly_label,
        anomaly_score=anomaly_score,
        health_score=health_score,
        near_term_failure_risk=failure_risk,
        will_fail_soon=1 if (analysis["predictive_health"]["will_fail_soon"] is True) else (0 if analysis["predictive_health"]["will_fail_soon"] is False else None),
        rul_days=rul_days if rul_days is not None else -1,
        risk_index=risk_index,
        risk_level=risk_level,
        recommendation_json=json.dumps(recommendation),
        created_at=datetime.utcnow()
    )
    db.add(db_analysis)
    db.commit()

    # 8. Assemble response
    return AnalysisResponse(
        analysis_id=analysis_id,
        pc=PCBase(
            pc_id=pc.pc_id,
            model_name=pc.model_name,
            department=pc.department,
            location=pc.location
        ),
        current_sensors=effective_sensors,
        engineered_features=analysis["engineered_features"],
        problem_analysis=analysis["problem_analysis"],
        predictive_health=analysis["predictive_health"],
        anomaly=analysis["anomaly"],
        explainability=analysis["explainability"],
        root_cause_candidates=recommendation["likely_root_causes"],
        similar_cases=similar_cases,
        recommendation=recommendation,
        forecasting=analysis["forecasting"],
        sensor_sources=sensor_sources,
        warnings=warnings
    )
