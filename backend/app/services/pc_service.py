from sqlalchemy.orm import Session
from datetime import datetime
from backend.app.models.database_models import PC, Telemetry
from backend.app.config import PC_CSV_PATH
import pandas as pd
import os

class PCService:
    @staticmethod
    def get_all_pcs(db: Session) -> list:
        return db.query(PC).all()

    @staticmethod
    def get_pc_by_id(db: Session, pc_id: str) -> PC:
        return db.query(PC).filter(PC.pc_id == pc_id).first()

    @staticmethod
    def get_telemetry_history(db: Session, pc_id: str, limit: int = 20) -> list:
        return db.query(Telemetry).filter(Telemetry.pc_id == pc_id).order_by(Telemetry.timestamp.asc()).limit(limit).all()

    @staticmethod
    def update_pc_sensors(
        db: Session, 
        pc_id: str, 
        cpu: float, 
        ram: float, 
        temp: float, 
        voltage: float, 
        disk: float, 
        fan: float
    ) -> PC:
        """Updates the current sensor readings of a PC and appends a record in the telemetry timeseries."""
        pc = db.query(PC).filter(PC.pc_id == pc_id).first()
        if not pc:
            return None
            
        # Update PC record
        pc.cpu_usage = cpu
        pc.ram_usage = ram
        pc.temperature = temp
        pc.voltage = voltage
        pc.disk_usage = disk
        pc.fan_speed = fan
        pc.last_updated = datetime.utcnow()
        
        # Append telemetry record
        telemetry = Telemetry(
            pc_id=pc_id,
            timestamp=datetime.utcnow(),
            cpu_usage=cpu,
            ram_usage=ram,
            temperature=temp,
            voltage=voltage,
            disk_usage=disk,
            fan_speed=fan
        )
        db.add(telemetry)
        db.commit()
        db.refresh(pc)
        
        # Keep CSV database in sync by exporting PC changes
        try:
            PCService.sync_database_to_csv(db)
        except Exception as e:
            print(f"PCService: Warning syncing to CSV: {str(e)}")
            
        return pc

    @staticmethod
    def sync_database_to_csv(db: Session):
        """Helper to sync the SQLite 'pcs' table back to the master organization_pcs.csv."""
        pcs = db.query(PC).all()
        records = []
        for pc in pcs:
            records.append({
                "PC_ID": pc.pc_id,
                "ModelName": pc.model_name,
                "Department": pc.department,
                "Location": pc.location,
                "CPUUsage": pc.cpu_usage,
                "RAMUsage": pc.ram_usage,
                "Temperature": pc.temperature,
                "Voltage": pc.voltage,
                "DiskUsage": pc.disk_usage,
                "FanSpeed": int(pc.fan_speed),
                "LastUpdated": pc.last_updated.isoformat()
            })
        df = pd.DataFrame(records)
        df.to_csv(PC_CSV_PATH, index=False)
