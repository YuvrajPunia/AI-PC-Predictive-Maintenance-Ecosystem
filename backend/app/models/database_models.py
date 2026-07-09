from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.database import Base

class PC(Base):
    __tablename__ = "pcs"
    
    pc_id = Column(String, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    location = Column(String, nullable=False)
    cpu_usage = Column(Float, nullable=True)
    ram_usage = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    voltage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)
    fan_speed = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    telemetry_records = relationship("Telemetry", back_populates="pc", cascade="all, delete-orphan")

class Telemetry(Base):
    __tablename__ = "telemetry"
    
    telemetry_id = Column(Integer, primary_key=True, autoincrement=True)
    pc_id = Column(String, ForeignKey("pcs.pc_id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    cpu_usage = Column(Float, nullable=True)
    ram_usage = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    voltage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)
    fan_speed = Column(Float, nullable=True)
    
    # Relationships
    pc = relationship("PC", back_populates="telemetry_records")

class RepairRecord(Base):
    __tablename__ = "repair_records"
    
    repair_id = Column(String, primary_key=True, index=True)
    pc_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_complaint = Column(Text, nullable=False)
    symptoms = Column(String, nullable=False)
    problem_detected = Column(String, nullable=False)
    confirmed_diagnosis = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=False)
    treatment_taken = Column(Text, nullable=False)
    downtime_minutes = Column(Integer, nullable=False)
    technician_notes = Column(Text, nullable=True)

class Complaint(Base):
    __tablename__ = "complaints"
    
    complaint_id = Column(Integer, primary_key=True, autoincrement=True)
    pc_id = Column(String, nullable=False)
    complaint_text = Column(Text, nullable=False)
    inferred_symptoms = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="Pending")  # e.g., "Pending", "Resolved"

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    analysis_id = Column(String, primary_key=True, index=True)
    complaint_id = Column(Integer, nullable=True)
    pc_id = Column(String, nullable=False)
    
    # Model classification
    predicted_problem = Column(String, nullable=True)
    prediction_confidence = Column(Float, nullable=True)
    
    # Anomaly detection
    anomaly_label = Column(String, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    
    # Predictive health scores
    health_score = Column(Float, nullable=True)
    near_term_failure_risk = Column(Float, nullable=True)
    will_fail_soon = Column(Integer, nullable=True)  # 0 or 1
    rul_days = Column(Integer, nullable=True)
    
    # Operational risk index
    risk_index = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)
    
    # Full generated recommendation content stored as JSON text
    recommendation_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
