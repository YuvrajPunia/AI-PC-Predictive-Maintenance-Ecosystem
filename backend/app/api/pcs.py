from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.app.database import get_db
from backend.app.models.schemas import PCRead, TelemetryRead, PCCreate
from backend.app.services.pc_service import PCService

router = APIRouter(prefix="/api/pcs", tags=["PCs"])

@router.get("", response_model=List[PCRead])
@router.get("/", response_model=List[PCRead])
def list_pcs(db: Session = Depends(get_db)):
    """Retrieves all registered PCs in the organization fleet."""
    return PCService.get_all_pcs(db)

@router.post("", response_model=PCRead)
@router.post("/", response_model=PCRead)
def register_pc(pc_in: PCCreate, db: Session = Depends(get_db)):
    """Registers a new PC asset in the fleet (sensors are optional)."""
    return PCService.register_pc(db, pc_in)

@router.get("/{pc_id}", response_model=PCRead)
def get_pc(pc_id: str, db: Session = Depends(get_db)):
    """Retrieves the current state and sensor metrics for a specific PC."""
    pc = PCService.get_pc_by_id(db, pc_id)
    if not pc:
        raise HTTPException(status_code=404, detail=f"PC with ID {pc_id} not found")
    return pc

@router.get("/{pc_id}/telemetry", response_model=List[TelemetryRead])
def get_pc_telemetry(pc_id: str, limit: int = 20, db: Session = Depends(get_db)):
    """Retrieves chronological historical sensor logs for linear trend forecasting."""
    pc = PCService.get_pc_by_id(db, pc_id)
    if not pc:
        raise HTTPException(status_code=404, detail=f"PC with ID {pc_id} not found")
    return PCService.get_telemetry_history(db, pc_id, limit)
