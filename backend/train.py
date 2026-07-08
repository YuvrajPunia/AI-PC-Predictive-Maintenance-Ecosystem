import os
import json
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, mean_absolute_error, r2_score, recall_score, precision_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

# Model families
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import MODELS_DIR, RAW_DATASET_PATH, PC_CSV_PATH, REPAIR_CSV_PATH
from backend.app.ml.feature_engineering.feature_engineer import FeatureEngineer
from backend.app.ml.explainability.explainer import PCExplainer
from backend.app.ml.clustering.clusterer import PCClusterer
from backend.app.services.embedding_service import OfflineEmbeddingService

def build_pipeline():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(BASE_DIR := os.path.abspath(__file__)), "visualizations"), exist_ok=True)
    metrics = {}

    print("==================================================")
    print("STARTING PC HEALTH & PREDICTIVE ML TRAINING PIPELINE")
    print("==================================================")

    # --------------------------------------------------
    # Step 1: Feature Engineering & Preprocessing Setup
    # --------------------------------------------------
    print("\n[Step 1] Loading raw motherboard telemetry dataset...")
    if not os.path.exists(RAW_DATASET_PATH):
        print(f"Error: Raw dataset not found at {RAW_DATASET_PATH}")
        return
        
    df_raw = pd.read_csv(RAW_DATASET_PATH)
    print(f"Loaded motherboard dataset. Shape: {df_raw.shape}")
    
    # Drop duplicates
    initial_len = len(df_raw)
    df_raw = df_raw.drop_duplicates()
    print(f"Removed {initial_len - len(df_raw)} duplicate rows.")
    
    # Initialize Feature Engineer
    fe = FeatureEngineer()
    df_engineered = fe.fit_transform(df_raw)
    df_engineered = fe.generate_engineered_targets(df_engineered)
    fe.save(MODELS_DIR)

    # Stratified train/test split based on ProblemDetected
    df_train, df_test = train_test_split(
        df_engineered,
        test_size=0.2,
        random_state=42,
        stratify=df_engineered['ProblemDetected']
    )
    print(f"Split data: Train size={len(df_train)}, Test size={len(df_test)}")

    # Define features
    num_features = [
        'CPUUsage', 'RAMUsage', 'Temperature', 'Voltage', 'DiskUsage', 'FanSpeed',
        'TemperatureStress', 'VoltageDeviation', 'CombinedLoad', 'ResourcePressureIndex',
        'CoolingEfficiencyProxy', 'FanTemperatureMismatch', 'ThermalLoadRatio', 
        'PowerInstabilityIndex', 'DiskStressIndex',
        'CPU_Temp_Interaction', 'RAM_CPU_Interaction', 'Temp_VoltageDev_Interaction',
        'Temp_FanSpeed_Ratio', 'Disk_CPU_Interaction', 'DegradationSeverityIndex'
    ]
    cat_features = ['ModelName']
    
    # Save explainer state
    explainer = PCExplainer(feature_names=num_features)
    # Fit explainer healthy medians from training dataset (ProblemDetected == No Problem)
    df_healthy = df_train[df_train['ProblemDetected'] == 'No Problem']
    for col in num_features:
        if col in df_healthy.columns:
            explainer.median_values[col] = float(df_healthy[col].median())
    explainer.save(MODELS_DIR)

    # Preprocessing pipelines
    num_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    cat_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer(transformers=[
        ('num', num_transformer, num_features),
        ('cat', cat_transformer, cat_features)
    ])
    
    # Fit preprocessor on training features
    X_train_raw = df_train[num_features + cat_features]
    X_test_raw = df_test[num_features + cat_features]
    
    preprocessor.fit(X_train_raw)
    joblib.dump(preprocessor, os.path.join(MODELS_DIR, 'problem_preprocessor.pkl'))
    print("Preprocessor fitted and saved.")
    
    # Process features
    X_train = preprocessor.transform(X_train_raw)
    X_test = preprocessor.transform(X_test_raw)
    
    # Get feature names after preprocessing (for explainers later)
    # Extract names
    cat_encoder = preprocessor.named_transformers_['cat'].named_steps['onehot']
    onehot_cols = cat_encoder.get_feature_names_out(cat_features).tolist()
    all_preprocessed_features = num_features + onehot_cols
    
    # --------------------------------------------------
    # Step 2: Sensor-Based Multiclass Problem Detection
    # --------------------------------------------------
    print("\n[Step 2] Training Sensor-Based Multiclass Problem Detection Classifier...")
    y_train = df_train['ProblemDetected']
    y_test = df_test['ProblemDetected']
    
    classifiers = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "RandomForestClassifier": RandomForestClassifier(n_estimators=100, random_state=42),
        "ExtraTreesClassifier": ExtraTreesClassifier(n_estimators=100, random_state=42),
        "HistGradientBoostingClassifier": HistGradientBoostingClassifier(random_state=42)
    }
    
    best_cls_f1 = -1
    best_cls = None
    best_cls_name = ""
    cls_metrics = {}
    
    for name, clf in classifiers.items():
        clf.fit(X_train, y_train)
        preds = clf.predict(X_test)
        acc = accuracy_score(y_test, preds)
        rec = recall_score(y_test, preds, average='macro')
        prec = precision_score(y_test, preds, average='macro')
        f1 = f1_score(y_test, preds, average='macro')
        
        cls_metrics[name] = {
            "accuracy": float(acc),
            "macro_precision": float(prec),
            "macro_recall": float(rec),
            "macro_f1": float(f1)
        }
        print(f" - {name}: Macro F1={f1:.4f}, Accuracy={acc:.4f}")
        
        if f1 > best_cls_f1:
            best_cls_f1 = f1
            best_cls = clf
            best_cls_name = name
            
    print(f"Selected Best Classifier: {best_cls_name} (Macro F1={best_cls_f1:.4f})")
    joblib.dump(best_cls, os.path.join(MODELS_DIR, 'problem_classifier.pkl'))
    metrics["problem_classification"] = {
        "selected_model": best_cls_name,
        "all_model_metrics": cls_metrics
    }

    # --------------------------------------------------
    # Step 3: Complaint-Based NLP Problem Classification
    # --------------------------------------------------
    print("\n[Step 3] Training Complaint-Based NLP Problem Classifier...")
    if os.path.exists(REPAIR_CSV_PATH):
        df_rep = pd.read_csv(REPAIR_CSV_PATH)
        df_rep = df_rep.dropna(subset=['UserComplaint', 'ProblemDetected'])
        
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        X_text = vectorizer.fit_transform(df_rep['UserComplaint'])
        y_text = df_rep['ProblemDetected']
        
        X_t_train, X_t_test, y_t_train, y_t_test = train_test_split(
            X_text, y_text, test_size=0.2, random_state=42, stratify=y_text
        )
        
        nlp_clf = LogisticRegression(random_state=42)
        nlp_clf.fit(X_t_train, y_t_train)
        
        preds_t = nlp_clf.predict(X_t_test)
        nlp_acc = accuracy_score(y_t_test, preds_t)
        nlp_f1 = f1_score(y_t_test, preds_t, average='macro')
        
        joblib.dump(vectorizer, os.path.join(MODELS_DIR, 'complaint_vectorizer.pkl'))
        joblib.dump(nlp_clf, os.path.join(MODELS_DIR, 'complaint_classifier.pkl'))
        
        metrics["complaint_nlp_classification"] = {
            "model": "TfidfVectorizer + LogisticRegression",
            "accuracy": float(nlp_acc),
            "macro_f1": float(nlp_f1)
        }
        print(f"NLP Classifier Trained: Macro F1={nlp_f1:.4f}, Accuracy={nlp_acc:.4f}")
    else:
        print("Warning: Repair history CSV not found. Skipping NLP classifier training.")

    # --------------------------------------------------
    # Step 4: Isolation Forest Anomaly Detection
    # --------------------------------------------------
    print("\n[Step 4] Training Isolation Forest Anomaly Detector...")
    # Train only on normal baseline records
    df_normal = df_train[df_train['ProblemDetected'] == 'No Problem']
    X_normal_sensors = df_normal[num_features]
    
    # Scale numerical inputs
    anomaly_scaler = StandardScaler()
    X_norm_scaled = anomaly_scaler.fit_transform(X_normal_sensors)
    
    iso_forest = IsolationForest(contamination=0.08, random_state=42)
    iso_forest.fit(X_norm_scaled)
    
    # Normalized score mapper
    # Raw scores are from decision_function (higher means less anomalous, negative means anomaly)
    # We map raw scores to [0, 1] where 0 is completely normal and 1 is highly anomalous.
    test_scores = iso_forest.decision_function(anomaly_scaler.transform(df_test[num_features]))
    min_score = float(test_scores.min())
    max_score = float(test_scores.max())
    
    joblib.dump(iso_forest, os.path.join(MODELS_DIR, 'anomaly_detector.pkl'))
    joblib.dump(anomaly_scaler, os.path.join(MODELS_DIR, 'anomaly_scaler.pkl'))
    
    metrics["anomaly_detection"] = {
        "model": "IsolationForest",
        "contamination": 0.08,
        "score_mapping_bounds": {"min_raw_decision": min_score, "max_raw_decision": max_score}
    }
    print(f"Isolation Forest Trained. Raw decision bounds: min={min_score:.4f}, max={max_score:.4f}")

    # --------------------------------------------------
    # Step 5: Health Score Prediction (Surrogate Regressor)
    # --------------------------------------------------
    print("\n[Step 5] Training Health Score Regressor...")
    y_h_train = df_train['HealthScore']
    y_h_test = df_test['HealthScore']
    
    regressors = {
        "LinearRegression": LinearRegression(),
        "RandomForestRegressor": RandomForestRegressor(n_estimators=100, random_state=42),
        "ExtraTreesRegressor": ExtraTreesRegressor(n_estimators=100, random_state=42),
        "GradientBoostingRegressor": GradientBoostingRegressor(random_state=42)
    }
    
    best_reg_mae = float('inf')
    best_reg = None
    best_reg_name = ""
    reg_metrics = {}
    
    for name, reg in regressors.items():
        reg.fit(X_train, y_h_train)
        preds = reg.predict(X_test)
        mae = mean_absolute_error(y_h_test, preds)
        r2 = r2_score(y_h_test, preds)
        
        reg_metrics[name] = {
            "mae": float(mae),
            "r2": float(r2)
        }
        print(f" - {name}: MAE={mae:.4f}, R2={r2:.4f}")
        
        if mae < best_reg_mae:
            best_reg_mae = mae
            best_reg = reg
            best_reg_name = name
            
    print(f"Selected Best Health Regressor: {best_reg_name} (MAE={best_reg_mae:.4f})")
    joblib.dump(best_reg, os.path.join(MODELS_DIR, 'health_regressor.pkl'))
    metrics["health_regression"] = {
        "selected_model": best_reg_name,
        "all_model_metrics": reg_metrics
    }

    # --------------------------------------------------
    # Step 6: Failure Risk and WillFailSoon Predictors
    # --------------------------------------------------
    print("\n[Step 6] Training Failure Risk Regressor and Classifier...")
    # Failure Probability Regressor
    y_f_train = df_train['FailureProbability']
    y_f_test = df_test['FailureProbability']
    
    fail_reg = RandomForestRegressor(n_estimators=100, random_state=42)
    fail_reg.fit(X_train, y_f_train)
    fail_reg_mae = mean_absolute_error(y_f_test, fail_reg.predict(X_test))
    joblib.dump(fail_reg, os.path.join(MODELS_DIR, 'failure_risk_regressor.pkl'))
    
    # WillFailSoon Classifier
    y_w_train = df_train['WillFailSoon']
    y_w_test = df_test['WillFailSoon']
    
    fail_cls = RandomForestClassifier(n_estimators=100, random_state=42)
    fail_cls.fit(X_train, y_w_train)
    fail_cls_acc = accuracy_score(y_w_test, fail_cls.predict(X_test))
    fail_cls_f1 = f1_score(y_w_test, fail_cls.predict(X_test), average='macro')
    joblib.dump(fail_cls, os.path.join(MODELS_DIR, 'failure_classifier.pkl'))
    
    metrics["failure_prediction"] = {
        "risk_regressor": "RandomForestRegressor",
        "risk_regressor_mae": float(fail_reg_mae),
        "will_fail_soon_classifier": "RandomForestClassifier",
        "will_fail_soon_accuracy": float(fail_cls_acc),
        "will_fail_soon_f1": float(fail_cls_f1)
    }
    print(f"Failure risk regressor MAE={fail_reg_mae:.4f}")
    print(f"WillFailSoon classifier Accuracy={fail_cls_acc:.4f}, F1={fail_cls_f1:.4f}")

    # --------------------------------------------------
    # Step 7: Remaining Useful Life Regressor
    # --------------------------------------------------
    print("\n[Step 7] Training Remaining Useful Life Regressor...")
    y_r_train = df_train['RemainingUsefulLifeDays']
    y_r_test = df_test['RemainingUsefulLifeDays']
    
    rul_reg = RandomForestRegressor(n_estimators=100, random_state=42)
    rul_reg.fit(X_train, y_r_train)
    rul_mae = mean_absolute_error(y_r_test, rul_reg.predict(X_test))
    joblib.dump(rul_reg, os.path.join(MODELS_DIR, 'rul_regressor.pkl'))
    
    metrics["rul_prediction"] = {
        "model": "RandomForestRegressor",
        "mae_days": float(rul_mae)
    }
    print(f"RUL Regressor trained. MAE={rul_mae:.2f} Days")

    # --------------------------------------------------
    # Step 8: Fleet K-Means Clustering
    # --------------------------------------------------
    print("\n[Step 8] Training Fleet K-Means Clusterer...")
    if os.path.exists(PC_CSV_PATH):
        df_pcs = pd.read_csv(PC_CSV_PATH)
        df_pcs_eng = fe.transform(df_pcs)
        
        clusterer = PCClusterer(n_clusters=4, random_state=42)
        clusterer.fit(df_pcs_eng, num_features)
        clusterer.save(MODELS_DIR)
        
        preds, names = clusterer.predict(df_pcs_eng, num_features)
        cluster_counts = pd.Series(names).value_counts().to_dict()
        
        metrics["fleet_clustering"] = {
            "model": "KMeans(k=4)",
            "clusters": clusterer.cluster_labels,
            "counts": cluster_counts
        }
        print(f"Fleet clusters derived: {cluster_counts}")
    else:
        print("Warning: PCs CSV not found. Skipping fleet clustering fit.")

    # --------------------------------------------------
    # Step 9: Build Repair Knowledge Base Embedding Index
    # --------------------------------------------------
    print("\n[Step 9] Initializing Repair Knowledge Base Semantic Embedding Index...")
    if os.path.exists(REPAIR_CSV_PATH):
        embedding_service = OfflineEmbeddingService()
        embedding_service.build_index_from_csv()
        print("Semantic indexing complete.")
    else:
        print("Warning: Repair history CSV not found. Skipping semantic indexing.")

    # Save metrics.json
    metrics["timestamp"] = datetime.now().isoformat()
    with open(os.path.join(MODELS_DIR, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=4)
    print("\nModel evaluation metrics saved to models/metrics.json")
    print("==================================================")
    print("ALL MODELS TRAINED AND ARTIFACTS SERIALIZED SUCCESSFULLY")
    print("==================================================")

if __name__ == "__main__":
    # Create the OfflineEmbeddingService dummy placeholder to allow importing during build_pipeline
    # We will write the embedding_service file next, but we can structure this to import correctly.
    build_pipeline()
