from sqlalchemy.orm import Session
from datetime import datetime
from backend.app.models.database_models import PC, Telemetry
from backend.app.models.schemas import PCCreate
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
    def register_pc(db: Session, pc_in: PCCreate) -> PC:
        """Registers a new PC asset with a generated unique ID and optional initial telemetry."""
        # Generate sequential PC_ID
        max_num = 0
        all_pcs = db.query(PC).all()
        for pc in all_pcs:
            if pc.pc_id.startswith("DRDO-PC-"):
                try:
                    num = int(pc.pc_id.split("-")[-1])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
                    
        new_pc_id = f"DRDO-PC-{max_num + 1:04d}"
        
        # Create PC record
        new_pc = PC(
            pc_id=new_pc_id,
            model_name=pc_in.model_name,
            department=pc_in.department,
            location=pc_in.location,
            cpu_usage=pc_in.cpu_usage,
            ram_usage=pc_in.ram_usage,
            temperature=pc_in.temperature,
            voltage=pc_in.voltage,
            disk_usage=pc_in.disk_usage,
            fan_speed=pc_in.fan_speed,
            last_updated=datetime.utcnow()
        )
        db.add(new_pc)
        
        # Append initial telemetry if any sensors are supplied
        has_sensors = any(
            getattr(pc_in, s) is not None
            for s in ["cpu_usage", "ram_usage", "temperature", "voltage", "disk_usage", "fan_speed"]
        )
        if has_sensors:
            telemetry = Telemetry(
                pc_id=new_pc_id,
                timestamp=datetime.utcnow(),
                cpu_usage=pc_in.cpu_usage,
                ram_usage=pc_in.ram_usage,
                temperature=pc_in.temperature,
                voltage=pc_in.voltage,
                disk_usage=pc_in.disk_usage,
                fan_speed=pc_in.fan_speed
            )
            db.add(telemetry)
            
        db.commit()
        db.refresh(new_pc)
        
        # Keep CSV in sync
        try:
            PCService.sync_database_to_csv(db)
            print(f"PCService: Registered {new_pc_id} and synced to CSV.")
        except Exception as e:
            print(f"PCService: Warning syncing to CSV: {str(e)}")
            
        return new_pc

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
                "FanSpeed": int(pc.fan_speed) if pc.fan_speed is not None else "",
                "LastUpdated": pc.last_updated.isoformat()
            })
        df = pd.DataFrame(records)
        df.to_csv(PC_CSV_PATH, index=False)
