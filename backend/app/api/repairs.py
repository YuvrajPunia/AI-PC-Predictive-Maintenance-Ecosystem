from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.app.database import get_db
from backend.app.models.schemas import RepairCompleteRequest, RepairResponse
from backend.app.services.repair_service import RepairService

router = APIRouter(prefix="/api/repairs", tags=["Repairs"])

@router.get("", response_model=List[RepairResponse])
def get_all_completed_repairs(limit: int = 100, db: Session = Depends(get_db)):
    """Retrieves list of all completed historical and new repairs in reverse chronological order."""
    return RepairService.get_all_repairs(db, limit)

@router.get("/{repair_id}", response_model=RepairResponse)
def get_repair_detail(repair_id: str, db: Session = Depends(get_db)):
    """Retrieves specific details of a completed repair case."""
    repair = RepairService.get_repair_by_id(db, repair_id)
    if not repair:
        raise HTTPException(status_code=404, detail=f"Repair case with ID '{repair_id}' not found.")
    return repair

@router.post("/complete", response_model=RepairResponse)
def complete_pc_repair(request: RepairCompleteRequest, db: Session = Depends(get_db)):
    """
    Records a finished technician repair resolution.
    Appends to the database, updates the master CSV, and refreshes the semantic embedding search index.
    """
    try:
        completed_repair = RepairService.complete_repair(db, request)
        return completed_repair
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record repair completion: {str(e)}")
