import os
import pandas as pd
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import PC_CSV_PATH, REPAIR_CSV_PATH, DATABASE_URL
from backend.app.database import engine, SessionLocal, Base
from backend.app.models.database_models import PC, RepairRecord, Telemetry

def seed_sqlite():
    print(f"Loading PC dataset from {PC_CSV_PATH}...")
    print(f"Loading Repair dataset from {REPAIR_CSV_PATH}...")
    
    if not os.path.exists(PC_CSV_PATH):
        print(f"Error: PC CSV not found at {PC_CSV_PATH}!")
        return
    if not os.path.exists(REPAIR_CSV_PATH):
        print(f"Error: Repair CSV not found at {REPAIR_CSV_PATH}!")
        return

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    # Clear existing tables
    db.query(PC).delete()
    db.query(RepairRecord).delete()
    db.query(Telemetry).delete()
    db.commit()
    
    # 2. Seed PCs and generate historical telemetry for forecasting
    df_pcs = pd.read_csv(PC_CSV_PATH)
    random.seed(42)
    
    print(f"Seeding {len(df_pcs)} PCs and creating telemetry histories...")
    for _, row in df_pcs.iterrows():
        try:
            last_updated_dt = datetime.fromisoformat(str(row["LastUpdated"]))
        except Exception:
            last_updated_dt = datetime.utcnow()
            
        pc_record = PC(
            pc_id=row["PC_ID"],
            model_name=row["ModelName"],
            department=row["Department"],
            location=row["Location"],
            cpu_usage=float(row["CPUUsage"]),
            ram_usage=float(row["RAMUsage"]),
            temperature=float(row["Temperature"]),
            voltage=float(row["Voltage"]),
            disk_usage=float(row["DiskUsage"]),
            fan_speed=float(row["FanSpeed"]),
            last_updated=last_updated_dt
        )
        db.add(pc_record)
        
        # Add 3 telemetry readings (simulated time history) for forecasting
        # T-2 days
        db.add(Telemetry(
            pc_id=row["PC_ID"],
            timestamp=last_updated_dt - timedelta(days=2),
            cpu_usage=max(0.0, float(row["CPUUsage"]) - random.uniform(-15.0, 15.0)),
            ram_usage=max(0.0, float(row["RAMUsage"]) - random.uniform(-8.0, 8.0)),
            temperature=max(0.0, float(row["Temperature"]) - random.uniform(-10.0, 10.0)),
            voltage=max(0.0, float(row["Voltage"]) - random.uniform(-0.5, 0.5)),
            disk_usage=max(0.0, float(row["DiskUsage"]) - 1.0),
            fan_speed=max(0.0, float(row["FanSpeed"]) - random.randint(-300, 300))
        ))
        # T-1 days
        db.add(Telemetry(
            pc_id=row["PC_ID"],
            timestamp=last_updated_dt - timedelta(days=1),
            cpu_usage=max(0.0, float(row["CPUUsage"]) - random.uniform(-8.0, 8.0)),
            ram_usage=max(0.0, float(row["RAMUsage"]) - random.uniform(-4.0, 4.0)),
            temperature=max(0.0, float(row["Temperature"]) - random.uniform(-5.0, 5.0)),
            voltage=max(0.0, float(row["Voltage"]) - random.uniform(-0.25, 0.25)),
            disk_usage=max(0.0, float(row["DiskUsage"]) - 0.5),
            fan_speed=max(0.0, float(row["FanSpeed"]) - random.randint(-150, 150))
        ))
        # Current (T-0)
        db.add(Telemetry(
            pc_id=row["PC_ID"],
            timestamp=last_updated_dt,
            cpu_usage=float(row["CPUUsage"]),
            ram_usage=float(row["RAMUsage"]),
            temperature=float(row["Temperature"]),
            voltage=float(row["Voltage"]),
            disk_usage=float(row["DiskUsage"]),
            fan_speed=float(row["FanSpeed"])
        ))
        
    db.commit()
    print("PCs and telemetry history successfully seeded.")
    
    # 3. Seed Repairs
    df_repairs = pd.read_csv(REPAIR_CSV_PATH)
    print(f"Seeding {len(df_repairs)} historical repair records...")
    for _, row in df_repairs.iterrows():
        try:
            timestamp_dt = datetime.fromisoformat(str(row["Timestamp"]))
        except Exception:
            timestamp_dt = datetime.utcnow()
            
        repair_record = RepairRecord(
            repair_id=row["Repair_ID"],
            pc_id=row["PC_ID"],
            timestamp=timestamp_dt,
            user_complaint=row["UserComplaint"],
            symptoms=row["Symptoms"],
            problem_detected=row["ProblemDetected"],
            confirmed_diagnosis=row["ConfirmedDiagnosis"],
            root_cause=row["RootCause"],
            treatment_taken=row["TreatmentTaken"],
            downtime_minutes=int(row["DowntimeMinutes"]),
            technician_notes=row["TechnicianNotes"] if pd.notnull(row["TechnicianNotes"]) else ""
        )
        db.add(repair_record)
        
    db.commit()
    db.close()
    print("Repair history successfully seeded.")

if __name__ == "__main__":
    seed_sqlite()
    print("Database seeding completed successfully.")
