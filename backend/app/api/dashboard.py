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

    # Load ML models
    health_reg = joblib.load(
        os.path.join(
            MODELS_DIR,
            "health_regressor.pkl"
        )
    )

    fail_reg = joblib.load(
        os.path.join(
            MODELS_DIR,
            "failure_risk_regressor.pkl"
        )
    )

    problem_preprocessor = joblib.load(
        os.path.join(
            MODELS_DIR,
            "problem_preprocessor.pkl"
        )
    )

    fe = joblib.load(fe_path)
    anom_model = joblib.load(anom_path)
    anom_scaler = joblib.load(anom_scaler_path)

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
    # Fleet ML analysis
    # ---------------------------------------------------------

    if total_pcs > 0:

        # Convert database PCs into DataFrame
        pc_records = []

        for pc in pcs:
            pc_records.append({
                "PC_ID": pc.pc_id,
                "ModelName": pc.model_name,
                "Department": pc.department,
                "Location": pc.location,
                "CPUUsage": pc.cpu_usage,
                "RAMUsage": pc.ram_usage,
                "Temperature": pc.temperature,
                "Voltage": pc.voltage,
                "DiskUsage": pc.disk_usage,
                "FanSpeed": pc.fan_speed,
            })

        df_pcs = pd.DataFrame(pc_records)

        # Feature engineering
        df_eng = fe.transform(df_pcs)

        # -----------------------------------------------------
        # Anomaly scoring
        # -----------------------------------------------------

        X_anom = df_eng[
            list(anom_scaler.feature_names_in_)
        ]

        X_anom_scaled = anom_scaler.transform(
            X_anom
        )

        anom_labels = anom_model.predict(
            X_anom_scaled
        )

        raw_scores = anom_model.decision_function(
            X_anom_scaled
        )

        anom_scores = 1.0 / (
            1.0 + np.exp(raw_scores * 8.0)
        )

        # -----------------------------------------------------
        # Health and failure predictions
        # -----------------------------------------------------

        X_all = problem_preprocessor.transform(
            df_eng
        )

        health_scores = health_reg.predict(
            X_all
        )

        failure_risks = fail_reg.predict(
            X_all
        )

        # -----------------------------------------------------
        # Aggregate fleet statistics
        # -----------------------------------------------------

        health_sum = 0.0

        for i, pc in enumerate(pcs):

            h = float(
                np.clip(
                    health_scores[i],
                    0.0,
                    100.0
                )
            )

            f = float(
                np.clip(
                    failure_risks[i],
                    0.0,
                    100.0
                )
            )

            a_label = (
                "Abnormal"
                if anom_labels[i] == -1
                else "Normal"
            )

            a_score = float(
                anom_scores[i]
            )

            # Calculate Risk Index
            r_index, r_level = (
                RiskService.calculate_risk_index(
                    h,
                    f,
                    a_score
                )
            )

            health_sum += h

            if a_label == "Abnormal":
                abnormal_count += 1

            if r_level in [
                "High",
                "Critical"
            ]:
                high_risk_count += 1

            if h < 50.0:
                critical_pc_count += 1

            risk_key = r_level.lower()

            if risk_key in risk_counts:
                risk_counts[risk_key] += 1

        avg_health = (
            health_sum / total_pcs
        )

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