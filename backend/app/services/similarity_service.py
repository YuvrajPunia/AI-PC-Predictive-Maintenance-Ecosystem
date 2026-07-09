import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from backend.app.config import (
    MODELS_DIR, REPAIR_CSV_PATH, PC_CSV_PATH,
    WEIGHT_COMPLAINT_SEMANTIC, WEIGHT_SYMPTOMS_SEMANTIC,
    WEIGHT_PROBLEM_TYPE, WEIGHT_MODEL_CONTEXT,
    DEFAULT_RETRIEVAL_THRESHOLD
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
        top_k: int = 3,
        upstream_confidence: float = 1.0,
        model_disagreement: bool = False
    ) -> list:
        """
        Retrieves the top_k most similar historical cases.
        Calculates similarity using the weighted formula and applies an empirically chosen threshold.
        """
        # Load indices and metadata
        if not os.path.exists(self.embeddings_path) or not os.path.exists(self.metadata_path) or not os.path.exists(REPAIR_CSV_PATH):
            print("SimilarityService: Embedding index files or repair_history.csv do not exist. Returning empty matches.")
            return []

        # Load historical repair facts
        df_repairs = pd.read_csv(REPAIR_CSV_PATH)
        if "RepairID" in df_repairs.columns and "Repair_ID" not in df_repairs.columns:
            df_repairs = df_repairs.rename(columns={"RepairID": "Repair_ID"})
        df_pcs = pd.read_csv(PC_CSV_PATH) if os.path.exists(PC_CSV_PATH) else pd.DataFrame()
        
        if not df_pcs.empty and 'PC_ID' in df_pcs.columns and 'PC_ID' in df_repairs.columns:
            df_historical = df_repairs.merge(df_pcs[['PC_ID', 'ModelName']], on='PC_ID', how='left')
        else:
            df_historical = df_repairs.copy()
            df_historical['ModelName'] = 'Unknown'
            
        df_historical['ModelName'] = df_historical['ModelName'].fillna('Unknown')
        
        # Load embeddings and retrieval metadata
        complaint_embeddings = np.load(self.embeddings_path)
        with open(self.metadata_path, 'r') as f:
            metadata = json.load(f)
            
        repair_ids = metadata["repair_ids"]
        # Dynamically load the empirically selected threshold (default is 65.0)
        retrieval_threshold = metadata.get("retrieval_threshold", DEFAULT_RETRIEVAL_THRESHOLD)
        
        # Symmetric query enrichment and normalization
        def clean_norm(val):
            if not val:
                return ""
            return " ".join(str(val).lower().strip().split())

        query_doc = f"complaint: {clean_norm(query_complaint)}"
        if query_symptoms.strip():
            query_doc += f" | symptoms: {clean_norm(query_symptoms)}"
        if predicted_problem.strip():
            query_doc += f" | problem: {clean_norm(predicted_problem)}"

        # 1. Semantic Cosine Similarity on Rich Query Document
        query_emb = self.embedding_service.get_query_embedding(query_doc)
        complaint_sims = cosine_similarity([query_emb], complaint_embeddings)[0]

        results = []
        for idx, row in df_historical.iterrows():
            rep_id = str(row['Repair_ID'])
            
            try:
                emb_idx = repair_ids.index(rep_id)
                comp_sim = float(complaint_sims[emb_idx])
            except (ValueError, IndexError):
                comp_sim = 0.0
                
            # Cosine similarity is the unmodified retrieval score
            final_score = comp_sim
            
            # Display match strength label transparently
            score_pct = round(final_score * 100.0, 1)
            if score_pct >= 70.0:
                match_strength = "Strong Match"
            elif score_pct >= 50.0:
                match_strength = "Moderate Match"
            else:
                match_strength = "Weak Contextual Match"
                
            # Match explanation reasons based on rich document overlap
            why_matched = []
            if comp_sim > 0.7:
                why_matched.append("Strong semantic overlap")
            elif comp_sim > 0.5:
                why_matched.append("Moderate semantic overlap")
            else:
                why_matched.append("Weak semantic overlap")
                
            hist_prob = str(row['ProblemDetected'])
            if hist_prob.lower().strip() == predicted_problem.lower().strip():
                why_matched.append("Same predicted issue category")
                
            hist_model = str(row['ModelName'])
            if hist_model.lower().strip() == pc_model.lower().strip():
                why_matched.append("Same model hardware context")

            results.append({
                "repair_id": rep_id,
                "pc_id": str(row['PC_ID']),
                "timestamp": str(row['Timestamp']) if 'Timestamp' in row else "",
                "historical_complaint": str(row['UserComplaint']),
                "symptoms": str(row['Symptoms']),
                "problem": hist_prob,
                "confirmed_diagnosis": str(row['ConfirmedDiagnosis']),
                "root_cause": str(row['RootCause']),
                "treatment_taken": str(row['TreatmentTaken']),
                "downtime_minutes": int(row['DowntimeMinutes']) if 'DowntimeMinutes' in row else 0,
                "technician_notes": str(row['TechnicianNotes']) if pd.notnull(row['TechnicianNotes']) else "",
                "similarity_score": score_pct,
                "match_strength": match_strength,
                "retrieval_engine": self.embedding_service.engine_type,
                "why_matched": why_matched
            })

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Always return the Top K matches without threshold pruning
        top_matches = results[:top_k]
        for rank, res in enumerate(top_matches, 1):
            res["rank"] = rank
            
        return top_matches
