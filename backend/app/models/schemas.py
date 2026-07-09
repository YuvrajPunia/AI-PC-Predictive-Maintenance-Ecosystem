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
    cpu_usage: Optional[float] = None
    ram_usage: Optional[float] = None
    temperature: Optional[float] = None
    voltage: Optional[float] = None
    disk_usage: Optional[float] = None
    fan_speed: Optional[float] = None
    last_updated: datetime

    class Config:
        from_attributes = True

# --- Telemetry schemas ---
class TelemetryRead(BaseModel):
    telemetry_id: int
    pc_id: str
    timestamp: datetime
    cpu_usage: Optional[float] = None
    ram_usage: Optional[float] = None
    temperature: Optional[float] = None
    voltage: Optional[float] = None
    disk_usage: Optional[float] = None
    fan_speed: Optional[float] = None

    class Config:
        from_attributes = True

# --- Analysis Request ---
class CurrentReadingsInput(BaseModel):
    temperature: Optional[float] = Field(None, ge=-20, le=150, description="Manual Temperature override in °C")
    fan_speed: Optional[float] = Field(None, ge=0, description="Manual Fan Speed override in RPM")
    cpu_usage: Optional[float] = Field(None, ge=0, le=100, description="Manual CPU usage override in %")
    ram_usage: Optional[float] = Field(None, ge=0, le=100, description="Manual RAM usage override in %")
    voltage: Optional[float] = Field(None, gt=0, le=30, description="Manual Voltage override in V")
    disk_usage: Optional[float] = Field(None, ge=0, le=100, description="Manual Disk usage override in %")

class AnalysisRequest(BaseModel):
    pc_id: str = Field(..., description="Unique identifier of the PC to analyze")
    complaint: str = Field(..., max_length=2000, description="The user complaint text")
    current_readings: Optional[CurrentReadingsInput] = None

# --- New PC Creation ---
class PCCreate(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=200, description="Hardware model name")
    department: str = Field(..., min_length=1, max_length=200, description="Department assignment")
    location: str = Field(..., min_length=1, max_length=200, description="Physical location")
    cpu_usage: Optional[float] = Field(None, ge=0, le=100)
    ram_usage: Optional[float] = Field(None, ge=0, le=100)
    temperature: Optional[float] = Field(None, ge=-50, le=200)
    voltage: Optional[float] = Field(None, gt=0, le=50)
    disk_usage: Optional[float] = Field(None, ge=0, le=100)
    fan_speed: Optional[float] = Field(None, ge=0, le=20000)

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
    match_strength: Optional[str] = None

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
    sensor_prediction: Optional[str] = None
    sensor_confidence: Optional[float] = None
    complaint_prediction: str
    complaint_confidence: float
    final_assessment: str
    agreement_status: str
    temperature_evidence_level: Optional[str] = None
    multi_fault_profile: Optional[Dict[str, Any]] = None

class PredictiveHealthDetail(BaseModel):
    health_score: Optional[float] = None
    health_band: Optional[str] = None
    near_term_failure_risk: Optional[float] = None
    will_fail_soon: Optional[bool] = None
    failure_confidence: Optional[float] = None
    remaining_useful_life_days: Optional[int] = None
    risk_index: Optional[float] = None
    risk_level: Optional[str] = None
    ood_flag: Optional[bool] = None
    ood_warning: Optional[str] = None

class AnomalyDetail(BaseModel):
    label: Optional[str] = None
    score: Optional[float] = None

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
    status: str  # "success", "insufficient_history", or "unavailable"

# --- Complete API Response for Complaint Analysis ---
class AnalysisResponse(BaseModel):
    analysis_id: str
    pc: PCBase
    current_sensors: Dict[str, Optional[float]]
    engineered_features: Dict[str, Optional[float]]
    problem_analysis: ProblemAnalysisDetail
    predictive_health: PredictiveHealthDetail
    anomaly: AnomalyDetail
    explainability: ExplainabilityDetail
    root_cause_candidates: List[str]
    similar_cases: List[SimilarRepairCase]
    recommendation: RecommendationDetail
    forecasting: ForecastDetail
    sensor_sources: Optional[Dict[str, Dict[str, Any]]] = None
    warnings: Optional[List[str]] = None

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
