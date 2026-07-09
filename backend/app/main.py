from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.app.api import pcs, predictions, repairs, dashboard
from backend.app.config import MODELS_DIR

app = FastAPI(
    title="AI-Powered PC Health & Repair Intelligence Ecosystem API",
    description="DRDO PC Fleet Health Analytics, Predictive Maintenance & Similar Repair Cases Semantic Retrieval Platform",
    version="1.0.0"
)

# Configure CORS for local React/Vite communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Safe for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(pcs.router)
app.include_router(predictions.router)
app.include_router(repairs.router)
app.include_router(dashboard.router)

@app.on_event("startup")
def startup_event():
    # Automatically initialize SQLite tables and seed if database is missing
    from backend.app.database import engine, SessionLocal, Base
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from backend.app.models.database_models import PC
        if db.query(PC).count() == 0:
            print("Database is empty. Seeding database automatically on startup...")
            from backend.seed_database import seed_sqlite
            seed_sqlite()
    except Exception as e:
        print(f"Error seeding database at startup: {e}")
    finally:
        db.close()

@app.get("/")
def root():
    return {
        "status": "Online",
        "system": "PC Health & Predictive Maintenance Platform API",
        "version": "1.0.0"
    }

@app.get("/api/health")
def api_health():
    """System diagnostic health check. Verifies the presence of key ML model binaries."""
    required_models = [
        'feature_engineer.pkl',
        'problem_preprocessor.pkl',
        'problem_classifier.pkl',
        'complaint_vectorizer.pkl',
        'complaint_classifier.pkl',
        'anomaly_detector.pkl',
        'anomaly_scaler.pkl',
        'ood_detector.pkl',
        'ood_scaler.pkl',
        'ood_metadata.json',
        'explainer.pkl',
        'repair_embeddings.npy',
        'repair_embedding_metadata.json'
    ]
    
    missing_models = []
    for model in required_models:
        model_path = os.path.join(MODELS_DIR, model)
        if not os.path.exists(model_path):
            missing_models.append(model)
            
    if missing_models:
        return {
            "status": "Degraded",
            "message": "Missing key serialized ML model artifacts.",
            "missing_artifacts": missing_models
        }
        
    return {
        "status": "Healthy",
        "message": "All ML models and database indices loaded successfully."
    }
