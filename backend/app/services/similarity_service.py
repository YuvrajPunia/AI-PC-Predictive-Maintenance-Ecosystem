import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from backend.app.config import (
    MODELS_DIR, REPAIR_CSV_PATH, PC_CSV_PATH,
    WEIGHT_COMPLAINT_SEMANTIC, WEIGHT_SYMPTOMS_SEMANTIC,
    WEIGHT_PROBLEM_TYPE, WEIGHT_MODEL_CONTEXT
)
from backend.app.services.embedding_service import OfflineEmbeddingService

class SimilarityService:
    def __init__(self):
        self.embedding_service = OfflineEmbeddingService()
        self.embeddings_path = self.embedding_service.embeddings_path
        self.metadata_path = self.embedding_service.metadata_path

    def retrieve_similar_cases(
        self, 
        query_complaint: str, 
        predicted_problem: str,
        pc_model: str,
        query_symptoms: str = "",
        top_k: int = 3
    ) -> list:
        """
        Retrieves the top_k most similar historical cases.
        Calculates similarity using the weighted formula:
        FinalSimilarity = 0.55 * ComplaintSemantic + 0.20 * SymptomsSemantic + 0.15 * ProblemType + 0.10 * ModelContext
        """
        # Load indices and metadata
        if not os.path.exists(self.embeddings_path) or not os.path.exists(self.metadata_path) or not os.path.exists(REPAIR_CSV_PATH):
            print("SimilarityService: Embedding index files or repair_history.csv do not exist. Returning empty matches.")
            return []

        # Load historical repair facts
        df_repairs = pd.read_csv(REPAIR_CSV_PATH)
        # Load PC details to get the historical PC model context
        df_pcs = pd.read_csv(PC_CSV_PATH) if os.path.exists(PC_CSV_PATH) else pd.DataFrame()
        
        # Merge repairs with PC models on PC_ID to get historical model names
        if not df_pcs.empty and 'PC_ID' in df_pcs.columns and 'PC_ID' in df_repairs.columns:
            df_historical = df_repairs.merge(df_pcs[['PC_ID', 'ModelName']], on='PC_ID', how='left')
        else:
            df_historical = df_repairs.copy()
            df_historical['ModelName'] = 'Unknown'
            
        df_historical['ModelName'] = df_historical['ModelName'].fillna('Unknown')
        
        # Load embeddings
        complaint_embeddings = np.load(self.embeddings_path)
        with open(self.metadata_path, 'r') as f:
            metadata = json.load(f)
            
        repair_ids = metadata["repair_ids"]
        
        # 1. Complaint Semantic Similarity (SBERT or TF-IDF)
        query_emb = self.embedding_service.get_query_embedding(query_complaint)
        complaint_sims = cosine_similarity([query_emb], complaint_embeddings)[0]
        
        # 2. Symptoms Semantic Similarity
        symptoms_sims = np.zeros(len(df_historical))
        has_symptoms = bool(query_symptoms and query_symptoms.strip())
        
        if has_symptoms:
            # Calculate TF-IDF similarities for symptoms text
            df_historical['Symptoms'] = df_historical['Symptoms'].fillna("").astype(str)
            all_sy = df_historical['Symptoms'].tolist() + [query_symptoms]
            
            symptom_vectorizer = TfidfVectorizer(stop_words='english')
            symptom_embs = symptom_vectorizer.fit_transform(all_sy).toarray()
            
            hist_sym_embs = symptom_embs[:-1]
            query_sym_emb = symptom_embs[-1]
            
            symptoms_sims = cosine_similarity([query_sym_emb], hist_sym_embs)[0]

        # Configurable weights
        w_complaint = WEIGHT_COMPLAINT_SEMANTIC
        w_symptoms = WEIGHT_SYMPTOMS_SEMANTIC if has_symptoms else 0.0
        w_problem = WEIGHT_PROBLEM_TYPE
        w_model = WEIGHT_MODEL_CONTEXT
        
        # Renormalize weights
        total_w = w_complaint + w_symptoms + w_problem + w_model
        w_complaint /= total_w
        if has_symptoms:
            w_symptoms /= total_w
        w_problem /= total_w
        w_model /= total_w

        results = []
        for idx, row in df_historical.iterrows():
            rep_id = str(row['Repair_ID'])
            
            # Find matching index in metadata mapping (since repair_ids size matches complaint_embeddings rows)
            try:
                emb_idx = repair_ids.index(rep_id)
                comp_sim = float(complaint_sims[emb_idx])
            except (ValueError, IndexError):
                comp_sim = 0.0
                
            # Problem Type Similarity (exact match on problem classification)
            hist_prob = str(row['ProblemDetected'])
            prob_sim = 1.0 if hist_prob.lower().strip() == predicted_problem.lower().strip() else 0.0
            
            # Model Name Similarity
            hist_model = str(row['ModelName'])
            model_sim = 1.0 if hist_model.lower().strip() == pc_model.lower().strip() else 0.0
            
            # Symptoms Similarity
            sym_sim = float(symptoms_sims[idx]) if has_symptoms else 0.0
            
            # Weighted Similarity
            final_score = (
                w_complaint * comp_sim +
                w_symptoms * sym_sim +
                w_problem * prob_sim +
                w_model * model_sim
            )
            
            # Match explanation reasons
            why_matched = []
            if comp_sim > 0.6:
                why_matched.append("Semantic complaint match")
            if prob_sim > 0.9:
                why_matched.append("Same predicted issue category")
            if has_symptoms and sym_sim > 0.5:
                why_matched.append("Similar symptoms profile")
            if model_sim > 0.9:
                why_matched.append("Same model hardware context")
                
            if not why_matched:
                why_matched.append("Telemetry/Context proximity")

            results.append({
                "repair_id": rep_id,
                "pc_id": str(row['PC_ID']),
                "timestamp": str(row['Timestamp']),
                "historical_complaint": str(row['UserComplaint']),
                "symptoms": str(row['Symptoms']),
                "problem": hist_prob,
                "confirmed_diagnosis": str(row['ConfirmedDiagnosis']),
                "root_cause": str(row['RootCause']),
                "treatment_taken": str(row['TreatmentTaken']),
                "downtime_minutes": int(row['DowntimeMinutes']),
                "technician_notes": str(row['TechnicianNotes']) if pd.notnull(row['TechnicianNotes']) else "",
                "similarity_score": round(float(final_score) * 100.0, 1),
                "retrieval_engine": self.embedding_service.engine_type,
                "why_matched": why_matched
            })

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Assign ranks
        for rank, res in enumerate(results[:top_k], 1):
            res["rank"] = rank
            
        return results[:top_k]
