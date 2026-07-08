from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- PC schemas ---
class PCBase(BaseModel):
    pc_id: str
    model_name: str
    department: str
    location: str

class PCRead(PCBase):
    cpu_usage: float
    ram_usage: float
    temperature: float
    voltage: float
    disk_usage: float
    fan_speed: float
    last_updated: datetime

    class Config:
        from_attributes = True

# --- Telemetry schemas ---
class TelemetryRead(BaseModel):
    telemetry_id: int
    pc_id: str
    timestamp: datetime
    cpu_usage: float
    ram_usage: float
    temperature: float
    voltage: float
    disk_usage: float
    fan_speed: float

    class Config:
        from_attributes = True

# --- Analysis Request ---
class AnalysisRequest(BaseModel):
    pc_id: str = Field(..., description="Unique identifier of the PC to analyze")
    complaint: str = Field(..., max_length=2000, description="The user complaint text")

# --- Similar Repairs schema ---
class SimilarRepairCase(BaseModel):
    rank: int
    repair_id: str
    similarity_score: float
    retrieval_engine: str
    pc_id: str
    historical_complaint: str
    symptoms: str
    problem: str
    confirmed_diagnosis: str
    root_cause: str
    treatment_taken: str
    downtime_minutes: int
    technician_notes: str
    why_matched: List[str]

# --- Recommendation Detail ---
class RecommendationDetail(BaseModel):
    primary_recommendation: str
    diagnostic_sequence: List[str]
    immediate_actions: List[str]
    preventive_actions: List[str]
    monitoring_actions: List[str]
    likely_root_causes: List[str]
    evidence_used: List[str]
    escalation_conditions: List[str]

# --- Model prediction components ---
class ProblemAnalysisDetail(BaseModel):
    sensor_prediction: str
    sensor_confidence: float
    complaint_prediction: str
    complaint_confidence: float
    final_assessment: str
    agreement_status: str

class PredictiveHealthDetail(BaseModel):
    health_score: float
    health_band: str
    near_term_failure_risk: float
    will_fail_soon: bool
    failure_confidence: float
    remaining_useful_life_days: int
    risk_index: float
    risk_level: str

class AnomalyDetail(BaseModel):
    label: str
    score: float

class ExplainabilityDetail(BaseModel):
    method: str
    top_contributing_features: List[Dict[str, Any]]

# --- Telemetry Forecast Detail ---
class ForecastDataPoint(BaseModel):
    timestamp: datetime
    value: float

class ForecastDetail(BaseModel):
    temperature_forecast: Optional[List[ForecastDataPoint]] = None
    voltage_forecast: Optional[List[ForecastDataPoint]] = None
    cpu_usage_forecast: Optional[List[ForecastDataPoint]] = None
    status: str  # "success" or "insufficient_history"

# --- Complete API Response for Complaint Analysis ---
class AnalysisResponse(BaseModel):
    analysis_id: str
    pc: PCBase
    current_sensors: Dict[str, float]
    engineered_features: Dict[str, float]
    problem_analysis: ProblemAnalysisDetail
    predictive_health: PredictiveHealthDetail
    anomaly: AnomalyDetail
    explainability: ExplainabilityDetail
    root_cause_candidates: List[str]
    similar_cases: List[SimilarRepairCase]
    recommendation: RecommendationDetail
    forecasting: ForecastDetail

# --- Repair Completion Request ---
class RepairCompleteRequest(BaseModel):
    pc_id: str
    original_complaint: str
    symptoms: str
    problem_detected: str
    confirmed_diagnosis: str = Field(..., max_length=1000)
    root_cause: str = Field(..., max_length=2000)
    treatment_taken: str = Field(..., max_length=2000)
    downtime_minutes: int = Field(..., ge=0, le=43200)  # maximum 30 days downtime
    technician_notes: Optional[str] = Field(None, max_length=5000)

class RepairResponse(BaseModel):
    repair_id: str
    pc_id: str
    timestamp: datetime
    user_complaint: str
    symptoms: str
    problem_detected: str
    confirmed_diagnosis: str
    root_cause: str
    treatment_taken: str
    downtime_minutes: int
    technician_notes: str

    class Config:
        from_attributes = True

# --- Dashboard Schemas ---
class OverviewStats(BaseModel):
    total_pcs: int
    average_health_score: float
    abnormal_pcs: int
    high_risk_pcs: int
    critical_pcs: int
    historical_repairs: int
    repairs_added_this_month: int

class RiskDistribution(BaseModel):
    low: int
    medium: int
    high: int
    critical: int

class ProblemCategoryCount(BaseModel):
    category: str
    count: int

class DepartmentRepairCount(BaseModel):
    department: str
    count: int

class DashboardOverviewResponse(BaseModel):
    stats: OverviewStats
    risk_distribution: RiskDistribution
    problem_distribution: List[ProblemCategoryCount]
    department_distribution: List[DepartmentRepairCount]
