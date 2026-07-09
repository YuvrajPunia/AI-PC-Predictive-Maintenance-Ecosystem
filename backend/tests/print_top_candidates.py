import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.services.similarity_service import SimilarityService
from backend.app.config import REPAIR_CSV_PATH

def print_candidates():
    print("==================================================")
    print("RAW TOP 10 CANDIDATES FOR: 'Experiencing overheating.'")
    print("==================================================")
    
    ss = SimilarityService()
    
    # We retrieve top_k = 10
    candidates = ss.retrieve_similar_cases(
        query_complaint="Experiencing overheating.",
        predicted_problem="Overheating",
        pc_model="HP Z2 G8",
        query_symptoms="",
        top_k=10
    )
    
    df_rep = pd.read_csv(REPAIR_CSV_PATH)
    if "RepairID" in df_rep.columns and "Repair_ID" not in df_rep.columns:
        df_rep = df_rep.rename(columns={"RepairID": "Repair_ID"})
        
    for i, c in enumerate(candidates, 1):
        # Find the source row index in CSV
        rep_id = c["repair_id"]
        row_idx = df_rep[df_rep['Repair_ID'] == rep_id].index[0]
        
        print(f"Rank {i}:")
        print(f"  - Similarity: {c['similarity_score']}% ({c['match_strength']})")
        print(f"  - Complaint: \"{c['historical_complaint']}\"")
        print(f"  - Diagnosed Problem: {c['problem']}")
        print(f"  - Repair Action (Treatment): {c['treatment_taken']}")
        print(f"  - Source CSV Row Index: {row_idx}")
        print(f"  - Why Matched: {c['why_matched']}")
        print("-" * 50)

if __name__ == "__main__":
    print_candidates()
