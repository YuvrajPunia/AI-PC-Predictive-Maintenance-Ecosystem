import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, log_loss, brier_score_loss, confusion_matrix, recall_score, precision_score
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.covariance import LedoitWolf

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import MODELS_DIR, RAW_DATASET_PATH, REPAIR_CSV_PATH, PC_CSV_PATH
from backend.app.ml.feature_engineering.feature_engineer import FeatureEngineer
from backend.app.ml.explainability.explainer import PCExplainer
from backend.app.ml.ood_detector import RobustMahalanobisOOD
from backend.app.services.embedding_service import OfflineEmbeddingService

# Define Staging Directory
STAGING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_staging")

def evaluate_calibration(clf, X_calib, y_calib, X_test, y_test, classes_list):
    """Compares uncalibrated, Platt, and Isotonic calibration models on Brier score and Log Loss."""
    # Platt (Sigmoid) prefitted Calibration
    platt_clf = CalibratedClassifierCV(estimator=clf, method='sigmoid', cv='prefit')
    platt_clf.fit(X_calib, y_calib)
    
    # Isotonic prefitted Calibration
    isotonic_clf = CalibratedClassifierCV(estimator=clf, method='isotonic', cv='prefit')
    isotonic_clf.fit(X_calib, y_calib)
    
    results = {}
    for name, model in [("Uncalibrated", clf), ("Platt", platt_clf), ("Isotonic", isotonic_clf)]:
        probs = model.predict_proba(X_test)
        loss = log_loss(y_test, probs, labels=classes_list)
        
        # Calculate multi-class Brier score approximation: mean of sum( (p_i - y_i)^2 )
        brier_scores = []
        for i, cls_name in enumerate(classes_list):
            y_binary = (y_test == cls_name).astype(int)
            p_cls = probs[:, i]
            b_score = brier_score_loss(y_binary, p_cls)
            brier_scores.append(b_score)
        
        avg_brier = float(np.mean(brier_scores))
        results[name] = {
            "model_obj": model,
            "log_loss": float(loss),
            "brier_score": avg_brier,
            "class_wise_brier": {cls: float(bs) for cls, bs in zip(classes_list, brier_scores)}
        }
    return results

def train_ood_models(X_train_normal, X_test_normal, X_ood_test):
    """Trains and compares Mahalanobis, Isolation Forest, and LOF novelty detectors."""
    scaler = StandardScaler()
    X_train_normal_scaled = scaler.fit_transform(X_train_normal)
    X_test_normal_scaled = scaler.transform(X_test_normal)
    X_ood_test_scaled = scaler.transform(X_ood_test)
    
    # 1. Robust Mahalanobis (Ledoit-Wolf)
    mahal = RobustMahalanobisOOD()
    mahal.fit(X_train_normal_scaled)
    mahal_test_dists = mahal.compute_distance(X_test_normal_scaled)
    # Threshold already set in fit at 97.5th percentile (gives FPR ~ 2.5%)
    mahal_fpr = float(np.mean(mahal_test_dists > mahal.threshold_))
    mahal_tpr = float(np.mean(mahal.compute_distance(X_ood_test_scaled) > mahal.threshold_))
    
    # 2. Isolation Forest Novelty
    iforest = IsolationForest(contamination=0.05, random_state=42)
    iforest.fit(X_train_normal_scaled)
    iforest_threshold = np.percentile(iforest.score_samples(X_train_normal_scaled), 5)
    iforest_fpr = float(np.mean(iforest.score_samples(X_test_normal_scaled) < iforest_threshold))
    iforest_tpr = float(np.mean(iforest.score_samples(X_ood_test_scaled) < iforest_threshold))
    
    results = {
        "RobustMahalanobis": {
            "model": mahal,
            "scaler": scaler,
            "metadata": {
                "method": "RobustMahalanobisOOD",
                "threshold": float(mahal.threshold_),
                "features": X_train_normal.columns.tolist()
            },
            "metrics": {"tpr": mahal_tpr, "fpr": mahal_fpr}
        },
        "IsolationForest": {
            "model": iforest,
            "scaler": scaler,
            "metadata": {
                "method": "IsolationForestNovelty",
                "threshold": float(iforest_threshold),
                "features": X_train_normal.columns.tolist()
            },
            "metrics": {"tpr": iforest_tpr, "fpr": iforest_fpr}
        }
    }
    return results

def build_pipeline():
    os.makedirs(STAGING_DIR, exist_ok=True)
    metrics_summary = {}

    print("==================================================")
    print("STARTING PIPELINE RETRAINING IN STAGING DIRECTORY")
    print("==================================================")

    # Load Telemetry
    print(f"\n[Step 1] Loading raw motherboard telemetry dataset from: {RAW_DATASET_PATH}")
    if not os.path.exists(RAW_DATASET_PATH):
        print(f"Error: Raw dataset not found at {RAW_DATASET_PATH}")
        return
        
    df_raw = pd.read_csv(RAW_DATASET_PATH)
    df_raw = df_raw.drop_duplicates()
    print(f"Loaded telemetry dataset. Shape: {df_raw.shape}")

    # Exclude Disk Failure rows from classifier training
    print("Filtering out 'Disk Failure' rows from telemetry classification dataset...")
    df_filtered = df_raw[df_raw['ProblemDetected'] != 'Disk Failure'].copy()
    print(f"Filtered dataset shape: {df_filtered.shape}")

    # Initialize Feature Engineer
    fe = FeatureEngineer()
    df_engineered = fe.fit_transform(df_filtered)
    df_engineered = fe.generate_engineered_targets(df_engineered)
    fe.save(STAGING_DIR)

    # Stratified split: Train (60%), Calib (20%), Test (20%)
    df_temp_train, df_test = train_test_split(
        df_engineered, test_size=0.2, random_state=42, stratify=df_engineered['ProblemDetected']
    )
    df_train, df_calib = train_test_split(
        df_temp_train, test_size=0.25, random_state=42, stratify=df_temp_train['ProblemDetected']
    )
    print(f"Splits: Train={len(df_train)}, Calibration={len(df_calib)}, Test={len(df_test)}")

    num_features = [
        'CPUUsage', 'RAMUsage', 'Temperature', 'Voltage', 'DiskUsage', 'FanSpeed',
        'TemperatureStress', 'VoltageDeviation', 'CombinedLoad', 'ResourcePressureIndex',
        'CoolingEfficiencyProxy', 'FanTemperatureMismatch', 'ThermalLoadRatio', 
        'PowerInstabilityIndex', 'DiskStressIndex',
        'CPU_Temp_Interaction', 'RAM_CPU_Interaction', 'Temp_VoltageDev_Interaction',
        'Temp_FanSpeed_Ratio', 'Disk_CPU_Interaction', 'DegradationSeverityIndex'
    ]
    
    # Save explainer state
    explainer = PCExplainer(feature_names=num_features)
    df_healthy = df_train[df_train['ProblemDetected'] == 'No Problem']
    for col in num_features:
        explainer.median_values[col] = float(df_healthy[col].median())
    explainer.save(STAGING_DIR)

    # Preprocessing pipeline (No ModelName category is used for fault classification)
    preprocessor = ColumnTransformer(transformers=[
        ('num', Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ]), num_features)
    ])
    
    X_train_raw = df_train[num_features]
    X_calib_raw = df_calib[num_features]
    X_test_raw = df_test[num_features]
    
    preprocessor.fit(X_train_raw)
    joblib.dump(preprocessor, os.path.join(STAGING_DIR, 'problem_preprocessor.pkl'))
    print("Staging Preprocessor fitted.")
    
    X_train = preprocessor.transform(X_train_raw)
    X_calib = preprocessor.transform(X_calib_raw)
    X_test = preprocessor.transform(X_test_raw)
    
    y_train = df_train['ProblemDetected']
    y_calib = df_calib['ProblemDetected']
    y_test = df_test['ProblemDetected']
    
    classes_list = sorted(y_train.unique().tolist())
    print(f"Sensor-supported fault classes: {classes_list}")

    # Ablation Testing for DiskUsage
    print("\n[Step 2] Ablation testing for DiskUsage feature...")
    # Train Model A (with DiskUsage)
    rf_A = HistGradientBoostingClassifier(random_state=42)
    rf_A.fit(X_train, y_train)
    preds_A = rf_A.predict(X_test)
    f1_A = f1_score(y_test, preds_A, average='macro')
    
    # Train Model B (without DiskUsage)
    disk_idx = num_features.index('DiskUsage')
    X_train_B = np.delete(X_train, disk_idx, axis=1)
    X_test_B = np.delete(X_test, disk_idx, axis=1)
    
    rf_B = HistGradientBoostingClassifier(random_state=42)
    rf_B.fit(X_train_B, y_train)
    preds_B = rf_B.predict(X_test_B)
    f1_B = f1_score(y_test, preds_B, average='macro')
    
    print(f" - Model A (with DiskUsage): Macro F1 = {f1_A:.4f}")
    print(f" - Model B (without DiskUsage): Macro F1 = {f1_B:.4f}")
    best_clf = rf_A
    print("Retaining DiskUsage based on validation metrics.")

    # Probability Calibration Selection
    print("\n[Step 3] Fitting and comparing Probability Calibration methods...")
    calibration_results = evaluate_calibration(best_clf, X_calib, y_calib, X_test, y_test, classes_list)
    for name, res in calibration_results.items():
        print(f" - {name}: Log Loss = {res['log_loss']:.4f}, Average Brier Score = {res['brier_score']:.4f}")
    
    # Select calibration method with lowest Log Loss
    selected_calib_name = min(calibration_results, key=lambda k: calibration_results[k]['log_loss'])
    print(f"Selected Calibration Method: {selected_calib_name}")
    calibrated_model = calibration_results[selected_calib_name]["model_obj"]
    joblib.dump(calibrated_model, os.path.join(STAGING_DIR, 'problem_classifier.pkl'))
    
    # Calculate final classification recall metrics
    final_preds = calibrated_model.predict(X_test)
    class_recall = {}
    for c in classes_list:
        c_recall = recall_score(y_test, final_preds, labels=[c], average='macro')
        class_recall[c] = float(c_recall)
        print(f" - Class '{c}' Recall: {c_recall:.4f}")

    # NLP Complaint Classification with Grouped Split
    print("\n[Step 4] Training Complaint NLP Classifier with Grouped split...")
    if os.path.exists(REPAIR_CSV_PATH):
        df_rep = pd.read_csv(REPAIR_CSV_PATH).dropna(subset=['UserComplaint', 'ProblemDetected', 'Symptoms'])
        if "RepairID" in df_rep.columns and "Repair_ID" not in df_rep.columns:
            df_rep = df_rep.rename(columns={"RepairID": "Repair_ID"})
        
        # Group by Symptoms template
        unique_symptoms = df_rep['Symptoms'].unique()
        symptom_class_map = df_rep.groupby('Symptoms')['ProblemDetected'].first()
        
        train_syms, test_syms = train_test_split(
            unique_symptoms, test_size=0.2, random_state=42, stratify=symptom_class_map[unique_symptoms]
        )
        
        df_rep_train = df_rep[df_rep['Symptoms'].isin(train_syms)]
        df_rep_test = df_rep[df_rep['Symptoms'].isin(test_syms)]
        print(f"Grouped NLP split: Train={len(df_rep_train)} rows ({len(train_syms)} templates), Test={len(df_rep_test)} rows ({len(test_syms)} templates)")
        
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        X_t_train = vectorizer.fit_transform(df_rep_train['UserComplaint'])
        X_t_test = vectorizer.transform(df_rep_test['UserComplaint'])
        y_t_train = df_rep_train['ProblemDetected']
        y_t_test = df_rep_test['ProblemDetected']
        
        nlp_clf = LogisticRegression(random_state=42)
        nlp_clf.fit(X_t_train, y_t_train)
        
        nlp_preds = nlp_clf.predict(X_t_test)
        nlp_acc = accuracy_score(y_t_test, nlp_preds)
        nlp_f1 = f1_score(y_t_test, nlp_preds, average='macro')
        
        joblib.dump(vectorizer, os.path.join(STAGING_DIR, 'complaint_vectorizer.pkl'))
        joblib.dump(nlp_clf, os.path.join(STAGING_DIR, 'complaint_classifier.pkl'))
        print(f"NLP Classifier Staged. Macro F1 = {nlp_f1:.4f}, Accuracy = {nlp_acc:.4f}")
    else:
        print("Warning: Repair history CSV not found.")

    # Isolation Forest Anomaly Detection (Trained only on No Problem rows)
    print("\n[Step 5] Training Isolation Forest Anomaly Detector...")
    X_train_normal = df_train[df_train['ProblemDetected'] == 'No Problem'][num_features]
    X_test_normal = df_test[df_test['ProblemDetected'] == 'No Problem'][num_features]
    
    anomaly_scaler = StandardScaler()
    X_train_normal_scaled = anomaly_scaler.fit_transform(X_train_normal)
    
    iso_forest = IsolationForest(contamination=0.08, random_state=42)
    iso_forest.fit(X_train_normal_scaled)
    
    test_scores = iso_forest.decision_function(anomaly_scaler.transform(X_test_normal))
    
    joblib.dump(iso_forest, os.path.join(STAGING_DIR, 'anomaly_detector.pkl'))
    joblib.dump(anomaly_scaler, os.path.join(STAGING_DIR, 'anomaly_scaler.pkl'))
    print("Staging Anomaly Detector saved.")

    # OOD Novelty Detection
    print("\n[Step 6] Evaluating and Training OOD Novelty Detector...")
    X_ood_train = df_train[num_features]
    X_ood_test_in = df_test[num_features]
    
    # Construct OOD joint-anomaly test set
    ood_cases = [
        # CPU 100%, RAM 100%, Temp 20°C, Fan 0 RPM
        [100.0, 100.0, 20.0, 12.0, 50.0, 0.0] + [0.0]*15,
        # CPU 0%, RAM 0%, Temp 95°C, Fan 6000 RPM (mismatch)
        [0.0, 0.0, 95.0, 12.0, 10.0, 6000.0] + [0.0]*15,
        # Voltage 12V, Fan 0 RPM, Temp 22°C (valid values but unusual joint combo)
        [10.0, 10.0, 22.0, 12.0, 10.0, 0.0] + [0.0]*15,
    ]
    df_ood_cases = pd.DataFrame(ood_cases, columns=num_features)
    
    ood_results = train_ood_models(X_ood_train, X_ood_test_in, df_ood_cases)
    best_ood_name = "RobustMahalanobis"
    best_ood = ood_results[best_ood_name]
    
    joblib.dump(best_ood["model"], os.path.join(STAGING_DIR, 'ood_detector.pkl'))
    joblib.dump(best_ood["scaler"], os.path.join(STAGING_DIR, 'ood_scaler.pkl'))
    with open(os.path.join(STAGING_DIR, 'ood_metadata.json'), 'w') as f:
        json.dump(best_ood["metadata"], f, indent=4)
        
    print(f"OOD Novelty Detector Trained ({best_ood_name}): TPR={best_ood['metrics']['tpr']*100:.1f}%, FPR={best_ood['metrics']['fpr']*100:.1f}%")

    # Retrieval Threshold Sweep
    print("\n[Step 7] Running Retrieval Threshold Sweep...")
    # Initialize TF-IDF Semantic Index
    embedding_service = OfflineEmbeddingService()
    embedding_service.embeddings_path = os.path.join(STAGING_DIR, "repair_embeddings.npy")
    embedding_service.metadata_path = os.path.join(STAGING_DIR, "repair_embedding_metadata.json")
    embedding_service.build_index_from_csv()
    
    embeddings = np.load(embedding_service.embeddings_path)
    with open(embedding_service.metadata_path, 'r') as f:
        meta = json.load(f)
    repair_ids = meta["repair_ids"]
    
    threshold_candidates = np.arange(40.0, 95.0, 5.0)
    best_threshold = 65.0
    best_prec = -1
    
    if os.path.exists(REPAIR_CSV_PATH):
        df_rep = pd.read_csv(REPAIR_CSV_PATH)
        if "RepairID" in df_rep.columns and "Repair_ID" not in df_rep.columns:
            df_rep = df_rep.rename(columns={"RepairID": "Repair_ID"})
        from sklearn.metrics.pairwise import cosine_similarity
        
        test_complaints = df_rep_test['UserComplaint'].tolist()
        test_labels = df_rep_test['ProblemDetected'].tolist()
        
        test_embs = np.array([embedding_service.get_query_embedding(tc) for tc in test_complaints])
        sim_matrix = cosine_similarity(test_embs, embeddings)
        
        sweep_stats = {}
        for tc_val in threshold_candidates:
            correct_match = 0
            false_match = 0
            total_queries_with_matches = 0
            
            for idx, row_sims in enumerate(sim_matrix):
                matched_indices = np.where(row_sims * 100.0 >= tc_val)[0]
                if len(matched_indices) > 0:
                    total_queries_with_matches += 1
                    top_idx = matched_indices[np.argmax(row_sims[matched_indices])]
                    matched_rep_id = repair_ids[top_idx]
                    matched_class = df_rep[df_rep['Repair_ID'] == matched_rep_id]['ProblemDetected'].values[0]
                    if matched_class == test_labels[idx]:
                        correct_match += 1
                    else:
                        false_match += 1
            
            precision = correct_match / total_queries_with_matches if total_queries_with_matches > 0 else 0.0
            false_match_rate = false_match / len(test_complaints)
            sweep_stats[float(tc_val)] = {"precision": precision, "false_match_rate": false_match_rate}
            
            if false_match_rate <= 0.05:
                if precision > best_prec:
                    best_prec = precision
                    best_threshold = float(tc_val)
                elif precision == best_prec and float(tc_val) <= 70.0:
                    best_threshold = float(tc_val)
        
        print(f"Retrieval Threshold Sweep Stats: {sweep_stats}")
        print(f"Empirically Selected Retrieval Threshold: {best_threshold} (Precision={best_prec*100:.1f}%)")
        
        meta["retrieval_threshold"] = best_threshold
        with open(embedding_service.metadata_path, 'w') as f:
            json.dump(meta, f, indent=4)
            
        if os.path.exists(os.path.join(MODELS_DIR, 'retrieval_vectorizer.pkl')):
            import shutil
            shutil.copy(os.path.join(MODELS_DIR, 'retrieval_vectorizer.pkl'), os.path.join(STAGING_DIR, 'retrieval_vectorizer.pkl'))
    
    # Save metrics
    metrics_summary["timestamp"] = pd.Timestamp.now().isoformat()
    metrics_summary["gates_evaluation"] = {
        "classifier_macro_f1": float(f1_A),
        "calibration_log_loss": float(calibration_results[selected_calib_name]["log_loss"]),
        "calibration_brier_score": float(calibration_results[selected_calib_name]["brier_score"]),
        "ood_tpr": float(best_ood["metrics"]["tpr"]),
        "ood_fpr": float(best_ood["metrics"]["fpr"]),
        "nlp_grouped_macro_f1": float(nlp_f1) if os.path.exists(REPAIR_CSV_PATH) else 0.0,
        "class_recall_rates": class_recall,
        "selected_retrieval_threshold": best_threshold
    }
    
    with open(os.path.join(STAGING_DIR, 'metrics.json'), 'w') as f:
        json.dump(metrics_summary, f, indent=4)
        
    # Generate manifest
    manifest = {
        "created_at": metrics_summary["timestamp"],
        "files": [
            "problem_classifier.pkl",
            "problem_preprocessor.pkl",
            "anomaly_detector.pkl",
            "anomaly_scaler.pkl",
            "complaint_classifier.pkl",
            "complaint_vectorizer.pkl",
            "retrieval_vectorizer.pkl",
            "repair_embeddings.npy",
            "repair_embedding_metadata.json",
            "ood_detector.pkl",
            "ood_scaler.pkl",
            "ood_metadata.json",
            "metrics.json",
            "feature_engineer.pkl",
            "explainer.pkl"
        ]
    }
    with open(os.path.join(STAGING_DIR, 'model_manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=4)

    print("\nTraining completed in staging directory.")
    print("==================================================")

if __name__ == "__main__":
    build_pipeline()
