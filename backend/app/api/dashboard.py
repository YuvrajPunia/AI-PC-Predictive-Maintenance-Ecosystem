from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import pandas as pd
import numpy as np
import os
import joblib

from backend.app.database import get_db
from backend.app.models.database_models import PC, RepairRecord
from backend.app.models.schemas import (
    DashboardOverviewResponse,
    OverviewStats,
    RiskDistribution,
    ProblemCategoryCount,
    DepartmentRepairCount,
)
from backend.app.services.risk_service import RiskService
from backend.app.config import MODELS_DIR


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse
)
def get_dashboard_overview(
    db: Session = Depends(get_db)
):
    """
    Computes real-time fleet analytics and historical statistics.

    1. Loads all PCs and calculates their current health,
       anomaly, and risk levels in memory.
    2. Retrieves completed repairs and calculates category
       and department distribution.
    """

    # ---------------------------------------------------------
    # 1. Load PCs and compute health / risk
    # ---------------------------------------------------------

    pcs = db.query(PC).all()
    total_pcs = len(pcs)

    # Model paths
    fe_path = os.path.join(
        MODELS_DIR,
        "feature_engineer.pkl"
    )

    anom_path = os.path.join(
        MODELS_DIR,
        "anomaly_detector.pkl"
    )

    anom_scaler_path = os.path.join(
        MODELS_DIR,
        "anomaly_scaler.pkl"
    )

    # Default dashboard values
    avg_health = 100.0
    abnormal_count = 0
    high_risk_count = 0
    critical_pc_count = 0

    risk_counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0,
    }

    # ---------------------------------------------------------
    # Fleet ML analysis using authoritative PredictionService
    # ---------------------------------------------------------
    if total_pcs > 0:
        from backend.app.services.prediction_service import PredictionService
        ps = PredictionService()

        health_sum = 0.0
        for pc in pcs:
            pc_dict = {
                "PC_ID": pc.pc_id,
                "ModelName": pc.model_name,
                "Department": pc.department,
                "Location": pc.location,
                "CPUUsage": pc.cpu_usage,
                "RAMUsage": pc.ram_usage,
                "Temperature": pc.temperature,
                "Voltage": pc.voltage,
                "DiskUsage": pc.disk_usage,
                "FanSpeed": pc.fan_speed
            }
            res = ps.run_inference(pc_dict, "")
            
            h = res["predictive_health"]["health_score"]
            r_level = res["predictive_health"]["risk_level"]
            is_anomaly = res["anomaly"]["score"] > 0.5 or res["predictive_health"]["ood_flag"]
            
            health_sum += h
            if is_anomaly:
                abnormal_count += 1

            if r_level in ["High", "Critical"]:
                high_risk_count += 1

            if h < 50.0:
                critical_pc_count += 1

            risk_key = r_level.lower()
            if risk_key in risk_counts:
                risk_counts[risk_key] += 1

        avg_health = health_sum / total_pcs

    # ---------------------------------------------------------
    # 2. Historical Repair Counts
    # ---------------------------------------------------------

    repairs = db.query(
        RepairRecord
    ).all()

    total_repairs = len(repairs)

    # Calculate repairs added this month
    this_month_start = (
        datetime.utcnow()
        .replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
    )

    repairs_this_month = (
        db.query(RepairRecord)
        .filter(
            RepairRecord.timestamp
            >= this_month_start
        )
        .count()
    )

    # ---------------------------------------------------------
    # Problem and department distributions
    # ---------------------------------------------------------

    prob_dist = {}
    dept_dist = {}

    for rep in repairs:

        cat = (
            rep.problem_detected
            if rep.problem_detected
            else "Unknown"
        )

        prob_dist[cat] = (
            prob_dist.get(cat, 0) + 1
        )

        # Map repair to PC department
        pc_obj = (
            db.query(PC)
            .filter(
                PC.pc_id == rep.pc_id
            )
            .first()
        )

        dept = (
            pc_obj.department
            if pc_obj
            else "Unknown"
        )

        dept_dist[dept] = (
            dept_dist.get(dept, 0) + 1
        )

    problem_distribution = [
        ProblemCategoryCount(
            category=k,
            count=v
        )
        for k, v in prob_dist.items()
    ]

    department_distribution = [
        DepartmentRepairCount(
            department=k,
            count=v
        )
        for k, v in dept_dist.items()
    ]

    # ---------------------------------------------------------
    # Final response
    # ---------------------------------------------------------

    return DashboardOverviewResponse(
        stats=OverviewStats(
            total_pcs=total_pcs,
            average_health_score=round(
                avg_health,
                1
            ),
            abnormal_pcs=abnormal_count,
            high_risk_pcs=high_risk_count,
            critical_pcs=critical_pc_count,
            historical_repairs=total_repairs,
            repairs_added_this_month=(
                repairs_this_month
            ),
        ),
        risk_distribution=RiskDistribution(
            low=risk_counts["low"],
            medium=risk_counts["medium"],
            high=risk_counts["high"],
            critical=risk_counts["critical"],
        ),
        problem_distribution=(
            problem_distribution
        ),
        department_distribution=(
            department_distribution
        ),
    )