import os
import pandas as pd
import pytest

from backend.app.config import PC_CSV_PATH, REPAIR_CSV_PATH

def test_pc_dataset_schema():
    assert os.path.exists(PC_CSV_PATH), f"PC CSV not found at {PC_CSV_PATH}"
    df = pd.read_csv(PC_CSV_PATH)
    
    expected_cols = [
        "PC_ID", "ModelName", "Department", "Location", 
        "CPUUsage", "RAMUsage", "Temperature", "Voltage", 
        "DiskUsage", "FanSpeed", "LastUpdated"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing required column {col} in PC dataset"

def test_pc_ids_unique():
    df = pd.read_csv(PC_CSV_PATH)
    assert df["PC_ID"].is_unique, "PC_ID column must contain unique values"

def test_repair_dataset_schema():
    assert os.path.exists(REPAIR_CSV_PATH), f"Repair CSV not found at {REPAIR_CSV_PATH}"
    df = pd.read_csv(REPAIR_CSV_PATH)
    
    expected_cols = [
        "Repair_ID", "PC_ID", "Timestamp", "UserComplaint", 
        "Symptoms", "ProblemDetected", "ConfirmedDiagnosis", 
        "RootCause", "TreatmentTaken", "DowntimeMinutes", "TechnicianNotes"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing required column {col} in Repair dataset"

def test_referential_integrity():
    df_pcs = pd.read_csv(PC_CSV_PATH)
    df_repairs = pd.read_csv(REPAIR_CSV_PATH)
    
    pc_ids = set(df_pcs["PC_ID"].tolist())
    repair_pc_ids = set(df_repairs["PC_ID"].dropna().tolist())
    
    # All PC_IDs in repair history must exist in the master PC assets registry
    missing_pcs = repair_pc_ids - pc_ids
    assert len(missing_pcs) == 0, f"Foreign key violation! PC_IDs in repairs do not exist in PCs: {missing_pcs}"
