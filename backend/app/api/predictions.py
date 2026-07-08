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
    2. Runs feature engineering and model prediction suite (Problem, Anomaly, Health, Failure, RUL).
    3. Retrieves top 3 similar historical completed repairs.
    4. Generates a new evidence-based recommendation.
    5. Saves records to the SQLite database.
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

    # 4. Run ML Models
    pc_row = {
        "PC_ID": pc.pc_id,
        "ModelName": pc.model_name,
        "Department": pc.department,
        "Location": pc.location,
        "CPUUsage": pc.cpu_usage,
        "RAMUsage": pc.ram_usage,
        "Temperature": pc.temperature,
        "Voltage": pc.voltage,
        "DiskUsage": pc.disk_usage,
        "FanSpeed": pc.fan_speed,
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
    
    # 5. Retrieve top 3 similar completed repairs
    similar_cases = similarity_service.retrieve_similar_cases(
        query_complaint=request.complaint,
        predicted_problem=fused_problem,
        pc_model=pc.model_name,
        query_symptoms=request.complaint,  # Use query complaint text as symptoms proxy if none other
        top_k=3
    )
    
    # Update complaint's inferred symptoms if any matches
    if similar_cases:
        db_complaint.inferred_symptoms = similar_cases[0]["symptoms"]
        db.commit()

    # 6. Generate structured AI Recommendation
    recommendation = RecommendationService.generate_recommendation(
        pc_id=pc.pc_id,
        complaint=request.complaint,
        fused_problem=fused_problem,
        health_score=health_score,
        failure_risk=failure_risk,
        rul_days=rul_days,
        anomaly_label=anomaly_label,
        sensors={
            "cpu_usage": pc.cpu_usage,
            "ram_usage": pc.ram_usage,
            "temperature": pc.temperature,
            "voltage": pc.voltage,
            "disk_usage": pc.disk_usage,
            "fan_speed": pc.fan_speed
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
        will_fail_soon=1 if analysis["predictive_health"]["will_fail_soon"] else 0,
        rul_days=rul_days,
        risk_index=analysis["predictive_health"]["risk_index"],
        risk_level=analysis["predictive_health"]["risk_level"],
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
        current_sensors={
            "cpu_usage": pc.cpu_usage,
            "ram_usage": pc.ram_usage,
            "temperature": pc.temperature,
            "voltage": pc.voltage,
            "disk_usage": pc.disk_usage,
            "fan_speed": pc.fan_speed
        },
        engineered_features=analysis["engineered_features"],
        problem_analysis=analysis["problem_analysis"],
        predictive_health=analysis["predictive_health"],
        anomaly=analysis["anomaly"],
        explainability=analysis["explainability"],
        root_cause_candidates=recommendation["likely_root_causes"],
        similar_cases=similar_cases,
        recommendation=recommendation,
        forecasting=analysis["forecasting"]
    )
