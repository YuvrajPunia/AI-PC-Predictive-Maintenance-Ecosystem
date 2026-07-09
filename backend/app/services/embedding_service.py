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
        self.embeddings_path = os.path.join(
            self.models_dir,
            "repair_embeddings.npy"
        )
        self.metadata_path = os.path.join(
            self.models_dir,
            "repair_embedding_metadata.json"
        )
        self.config_path = os.path.join(
            self.models_dir,
            "embedding_config.json"
        )

        self.engine_type = "TF-IDF"
        self.model = None
        self.vectorizer = None

        self._load_model()

    def _load_model(self):
        """
        Loads the embedding model (tries SBERT, falls back to TF-IDF if unavailable).
        """
        # Try SBERT if sentence-transformers is installed.
        try:
            # Try offline loading first
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(
                "all-MiniLM-L6-v2",
                device="cpu"
            )
            self.engine_type = "SBERT"
            print("EmbeddingService: Successfully loaded SentenceTransformer offline.")
            self._save_config()
            return
        except Exception as e_offline:
            print(f"EmbeddingService: Offline SBERT load failed ({e_offline}). Trying online load...")
            try:
                # Try online downloading (useful on Render/fresh setups)
                os.environ["TRANSFORMERS_OFFLINE"] = "0"
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(
                    "all-MiniLM-L6-v2",
                    device="cpu"
                )
                self.engine_type = "SBERT"
                print("EmbeddingService: Successfully downloaded/loaded SentenceTransformer online.")
                self._save_config()
                return
            except Exception as e_online:
                print(f"EmbeddingService: Online SBERT load failed ({e_online}). Falling back to TF-IDF.")

        # Lightweight fallback
        self.engine_type = "TF-IDF"
        self.model = None
        self._save_config()

    def _save_config(self):
        os.makedirs(
            self.models_dir,
            exist_ok=True
        )

        with open(
            self.config_path,
            "w"
        ) as f:
            json.dump(
                {
                    "engine_type": self.engine_type
                },
                f
            )

    def build_index_from_csv(self):
        """
        Generates embeddings for all completed repairs
        in repair_history.csv and saves them.
        """

        if not os.path.exists(REPAIR_CSV_PATH):
            print(
                f"Error: {REPAIR_CSV_PATH} not found. "
                "Cannot build embedding index."
            )
            return

        df = pd.read_csv(REPAIR_CSV_PATH)
        if "RepairID" in df.columns and "Repair_ID" not in df.columns:
            df = df.rename(columns={"RepairID": "Repair_ID"})

        # Create richer retrieval documents with normalized text fields
        def clean_norm(val):
            if pd.isnull(val):
                return ""
            return " ".join(str(val).lower().strip().split())

        rich_docs = []
        for _, row in df.iterrows():
            comp = clean_norm(row.get("UserComplaint", ""))
            symp = clean_norm(row.get("Symptoms", ""))
            prob = clean_norm(row.get("ProblemDetected", ""))
            treat = clean_norm(row.get("TreatmentTaken", ""))
            
            doc = f"complaint: {comp}"
            if symp:
                doc += f" | symptoms: {symp}"
            if prob:
                doc += f" | problem: {prob}"
            if treat:
                doc += f" | treatment: {treat}"
            rich_docs.append(doc)

        repair_ids = df["Repair_ID"].tolist()

        print(
            f"Building semantic index for "
            f"{len(rich_docs)} rich repair documents "
            f"using {self.engine_type}..."
        )

        if self.engine_type == "SBERT":
            embeddings = self.model.encode(
                rich_docs,
                show_progress_bar=False
            )

        else:
            # Fit lightweight TF-IDF model
            self.vectorizer = TfidfVectorizer(
                max_features=500,
                stop_words="english"
            )

            embeddings = (
                self.vectorizer
                .fit_transform(rich_docs)
                .toarray()
            )

            # Save fitted vectorizer for future queries
            joblib.dump(
                self.vectorizer,
                os.path.join(
                    self.models_dir,
                    "retrieval_vectorizer.pkl"
                )
            )

        # Save embeddings matrix
        np.save(
            self.embeddings_path,
            np.array(
                embeddings,
                dtype=np.float32
            )
        )

        # Save repair ID mapping
        metadata = {
            "repair_ids": [
                str(rid)
                for rid in repair_ids
            ]
        }

        with open(
            self.metadata_path,
            "w"
        ) as f:
            json.dump(
                metadata,
                f,
                indent=4
            )

        print(
            f"Semantic index saved: "
            f"{self.embeddings_path} "
            f"and {self.metadata_path}"
        )

    def get_query_embedding(
        self,
        query_text: str
    ) -> np.ndarray:
        """
        Converts query text into an embedding vector
        based on the current engine.
        """

        if self.engine_type == "SBERT":
            return self.model.encode(
                [query_text],
                show_progress_bar=False
            )[0]

        # TF-IDF mode
        vec_path = os.path.join(
            self.models_dir,
            "retrieval_vectorizer.pkl"
        )

        if (
            self.vectorizer is None
            and os.path.exists(vec_path)
        ):
            self.vectorizer = joblib.load(
                vec_path
            )

        if self.vectorizer is None:
            # Safe fallback if vectorizer is unavailable
            return np.zeros(
                500,
                dtype=np.float32
            )

        return (
            self.vectorizer
            .transform([query_text])
            .toarray()[0]
        )

    def add_single_to_index(
        self,
        repair_id: str,
        complaint_text: str
    ):
        """
        Appends a new repair record to the cached
        embeddings and metadata files.
        """

        # Generate embedding
        new_emb = self.get_query_embedding(
            complaint_text
        )

        # Load existing embeddings
        if os.path.exists(
            self.embeddings_path
        ):
            embeddings = np.load(
                self.embeddings_path
            )

            embeddings = np.vstack(
                [
                    embeddings,
                    new_emb
                ]
            )

        else:
            embeddings = np.array(
                [new_emb],
                dtype=np.float32
            )

        # Save updated embeddings
        np.save(
            self.embeddings_path,
            embeddings.astype(
                np.float32
            )
        )

        # Load metadata
        if os.path.exists(
            self.metadata_path
        ):
            with open(
                self.metadata_path,
                "r"
            ) as f:
                metadata = json.load(f)

        else:
            metadata = {
                "repair_ids": []
            }

        # Add new repair ID
        metadata["repair_ids"].append(
            str(repair_id)
        )

        # Save metadata
        with open(
            self.metadata_path,
            "w"
        ) as f:
            json.dump(
                metadata,
                f,
                indent=4
            )

        print(
            f"EmbeddingService: Successfully indexed "
            f"new repair {repair_id} "
            f"in {self.engine_type} space."
        )