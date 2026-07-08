import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.app.config import MODELS_DIR, REPAIR_CSV_PATH

class OfflineEmbeddingService:
    def __init__(self):
        self.models_dir = MODELS_DIR
        self.embeddings_path = os.path.join(self.models_dir, "repair_embeddings.npy")
        self.metadata_path = os.path.join(self.models_dir, "repair_embedding_metadata.json")
        self.config_path = os.path.join(self.models_dir, "embedding_config.json")
        
        self.engine_type = "TF-IDF"  # Fallback by default
        self.model = None
        self.vectorizer = None
        self._load_model()

    def _load_model(self):
        """Attempts to load SentenceTransformer; falls back to TF-IDF if it fails."""
        # 1. Attempt SBERT
        try:
            from sentence_transformers import SentenceTransformer
            # Disable online checks to avoid hangs if offline
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            self.engine_type = "SBERT"
            print("EmbeddingService: Successfully loaded SentenceTransformer (all-MiniLM-L6-v2) engine.")
            self._save_config()
            return
        except Exception as e:
            print(f"EmbeddingService: SBERT load skipped or failed ({str(e)}). Falling back to TF-IDF engine.")
            
        # 2. Setup TF-IDF Fallback
        self.engine_type = "TF-IDF"
        self._save_config()

    def _save_config(self):
        os.makedirs(self.models_dir, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump({"engine_type": self.engine_type}, f)

    def build_index_from_csv(self):
        """Generates embeddings for all completed repairs in repair_history.csv and saves them."""
        if not os.path.exists(REPAIR_CSV_PATH):
            print(f"Error: {REPAIR_CSV_PATH} not found. Cannot build embedding index.")
            return
            
        df = pd.read_csv(REPAIR_CSV_PATH)
        # Ensure text is filled
        df['UserComplaint'] = df['UserComplaint'].fillna("").astype(str)
        complaints = df['UserComplaint'].tolist()
        repair_ids = df['Repair_ID'].tolist()
        
        print(f"Building semantic index for {len(complaints)} repair complaints using {self.engine_type}...")
        
        if self.engine_type == "SBERT":
            embeddings = self.model.encode(complaints, show_progress_bar=False)
        else:
            # Fit TF-IDF on all complaints
            self.vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
            embeddings = self.vectorizer.fit_transform(complaints).toarray()
            # Save fitted TF-IDF vectorizer for online query transformation
            joblib.dump(self.vectorizer, os.path.join(self.models_dir, "retrieval_vectorizer.pkl"))
            
        # Save embeddings matrix
        np.save(self.embeddings_path, np.array(embeddings, dtype=np.float32))
        
        # Save metadata mapping: list of repair ids
        metadata = {"repair_ids": [str(rid) for rid in repair_ids]}
        with open(self.metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
            
        print(f"Semantic index saved: {self.embeddings_path} and {self.metadata_path}")

    def get_query_embedding(self, query_text: str) -> np.ndarray:
        """Converts query text into an embedding vector based on current engine."""
        if self.engine_type == "SBERT":
            return self.model.encode([query_text], show_progress_bar=False)[0]
        else:
            # Load vectorizer
            vec_path = os.path.join(self.models_dir, "retrieval_vectorizer.pkl")
            if not self.vectorizer and os.path.exists(vec_path):
                self.vectorizer = joblib.load(vec_path)
            
            if not self.vectorizer:
                # If vectorizer not fitted yet, return dummy
                return np.zeros(500, dtype=np.float32)
                
            return self.vectorizer.transform([query_text]).toarray()[0]

    def add_single_to_index(self, repair_id: str, complaint_text: str):
        """Appends a new repair record to the cached embeddings and metadata files."""
        # 1. Generate query embedding
        new_emb = self.get_query_embedding(complaint_text)
        
        # 2. Load existing embeddings
        if os.path.exists(self.embeddings_path):
            embeddings = np.load(self.embeddings_path)
            embeddings = np.vstack([embeddings, new_emb])
        else:
            embeddings = np.array([new_emb], dtype=np.float32)
            
        np.save(self.embeddings_path, embeddings.astype(np.float32))
        
        # 3. Load existing metadata
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {"repair_ids": []}
            
        metadata["repair_ids"].append(str(repair_id))
        
        with open(self.metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
            
        print(f"EmbeddingService: Successfully indexed new repair {repair_id} in {self.engine_type} space.")
