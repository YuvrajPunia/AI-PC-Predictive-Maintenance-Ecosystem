from sqlalchemy.orm import Session
from datetime import datetime
import pandas as pd
import os
from backend.app.models.database_models import RepairRecord, Complaint
from backend.app.models.schemas import RepairCompleteRequest
from backend.app.config import REPAIR_CSV_PATH
from backend.app.services.embedding_service import OfflineEmbeddingService

class RepairService:
    @staticmethod
    def get_all_repairs(db: Session, limit: int = 100) -> list:
        return db.query(RepairRecord).order_by(RepairRecord.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_repair_by_id(db: Session, repair_id: str) -> RepairRecord:
        return db.query(RepairRecord).filter(RepairRecord.repair_id == repair_id).first()

    @staticmethod
    def complete_repair(db: Session, request: RepairCompleteRequest) -> RepairRecord:
        """
        Processes a completed repair:
        1. Auto-generates unique Repair_ID.
        2. Saves to SQLite database.
        3. Appends safely to repair_history.csv.
        4. Triggers incremental semantic index update.
        """
        # Generate new Repair ID
        # Read existing records from DB to find the highest number
        max_id_num = 0
        last_repair = db.query(RepairRecord).order_by(RepairRecord.repair_id.desc()).first()
        if last_repair and last_repair.repair_id.startswith("REP-"):
            try:
                max_id_num = int(last_repair.repair_id.split("-")[1])
            except (IndexError, ValueError):
                pass
                
        # Fallback to CSV check if DB is empty
        if max_id_num == 0 and os.path.exists(REPAIR_CSV_PATH):
            try:
                df = pd.read_csv(REPAIR_CSV_PATH)
                if not df.empty and 'Repair_ID' in df.columns:
                    rep_ids = df['Repair_ID'].dropna().tolist()
                    id_nums = []
                    for rid in rep_ids:
                        if str(rid).startswith("REP-"):
                            try:
                                id_nums.append(int(str(rid).split("-")[1]))
                            except ValueError:
                                pass
                    if id_nums:
                        max_id_num = max(id_nums)
            except Exception:
                pass
                
        new_id_num = max_id_num + 1
        new_repair_id = f"REP-{new_id_num:05d}"
        
        # Save to database
        db_repair = RepairRecord(
            repair_id=new_repair_id,
            pc_id=request.pc_id,
            timestamp=datetime.utcnow(),
            user_complaint=request.original_complaint,
            symptoms=request.symptoms,
            problem_detected=request.problem_detected,
            confirmed_diagnosis=request.confirmed_diagnosis,
            root_cause=request.root_cause,
            treatment_taken=request.treatment_taken,
            downtime_minutes=request.downtime_minutes,
            technician_notes=request.technician_notes or ""
        )
        db.add(db_repair)
        
        # Mark any active complaint for this PC as resolved
        active_complaint = db.query(Complaint).filter(
            Complaint.pc_id == request.pc_id, 
            Complaint.status == "Pending"
        ).order_by(Complaint.created_at.desc()).first()
        if active_complaint:
            active_complaint.status = "Resolved"
            
        db.commit()
        db.refresh(db_repair)
        
        # Append to repair_history.csv
        try:
            RepairService.append_to_csv(db_repair)
        except Exception as e:
            print(f"RepairService: Warning appending to CSV: {str(e)}")
            
        # Trigger incremental semantic index update
        try:
            emb_service = OfflineEmbeddingService()
            emb_service.add_single_to_index(new_repair_id, request.original_complaint)
        except Exception as e:
            print(f"RepairService: Warning updating embedding index: {str(e)}")
            
        return db_repair

    @staticmethod
    def append_to_csv(repair: RepairRecord):
        """Appends a new completed repair record to the master CSV knowledge base."""
        new_row = {
            "Repair_ID": repair.repair_id,
            "PC_ID": repair.pc_id,
            "Timestamp": repair.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "UserComplaint": repair.user_complaint,
            "Symptoms": repair.symptoms,
            "ProblemDetected": repair.problem_detected,
            "ConfirmedDiagnosis": repair.confirmed_diagnosis,
            "RootCause": repair.root_cause,
            "TreatmentTaken": repair.treatment_taken,
            "DowntimeMinutes": repair.downtime_minutes,
            "TechnicianNotes": repair.technician_notes
        }
        
        if os.path.exists(REPAIR_CSV_PATH):
            df_new = pd.DataFrame([new_row])
            df_new.to_csv(REPAIR_CSV_PATH, mode='a', header=False, index=False)
            print(f"RepairService: Appended {repair.repair_id} to CSV.")
        else:
            df_new = pd.DataFrame([new_row])
            df_new.to_csv(REPAIR_CSV_PATH, index=False)
            print(f"RepairService: Created and wrote {repair.repair_id} to CSV.")
