import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.services.embedding_service import OfflineEmbeddingService

def rebuild():
    print("==================================================")
    print("REBUILDING SEMANTIC RETRIEVAL INDEX")
    print("==================================================")
    
    # We override models directory to models folder directly
    es = OfflineEmbeddingService()
    print(f"Index Embeddings Path: {es.embeddings_path}")
    print(f"Index Metadata Path: {es.metadata_path}")
    
    es.build_index_from_csv()
    
    # Verify count
    import numpy as np
    import json
    
    embs = np.load(es.embeddings_path)
    with open(es.metadata_path, 'r') as f:
        meta = json.load(f)
        
    print(f"Verification: Embeddings shape = {embs.shape}")
    print(f"Verification: Metadata repair IDs count = {len(meta['repair_ids'])}")
    assert len(embs) == len(meta['repair_ids']), "Mismatch between embeddings and metadata counts!"
    print("Index rebuild and verification completed successfully!")

if __name__ == "__main__":
    rebuild()
