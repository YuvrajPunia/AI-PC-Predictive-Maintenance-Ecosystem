import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.services.similarity_service import SimilarityService

def run_tests():
    print("==================================================")
    print("RUNNING HISTORICAL RETRIEVAL PERFORMANCE CHECKS")
    print("==================================================")
    
    ss = SimilarityService()
    
    queries = [
        ("Experiencing overheating.", "Overheating"),
        ("System becomes extremely hot and fan runs loudly.", "Overheating"),
        ("Computer is very slow and memory usage keeps increasing.", "Memory Leak"),
        ("PC suddenly shuts down and power is unstable.", "Power Issue"),
        ("Disk errors and corrupted files are appearing.", "Disk Failure")
    ]
    
    for idx, (query_text, pred_prob) in enumerate(queries, 1):
        print(f"\n[Query {idx}] \"{query_text}\" (Assumed category: {pred_prob})")
        results = ss.retrieve_similar_cases(
            query_complaint=query_text,
            predicted_problem=pred_prob,
            pc_model="HP Z2 G8",
            query_symptoms="",
            top_k=3
        )
        
        for r in results:
            print(f"  Rank {r['rank']}: {r['repair_id']}")
            print(f"    - Score: {r['similarity_score']}% ({r['match_strength']})")
            print(f"    - Complaint: \"{r['historical_complaint']}\"")
            print(f"    - Diagnosed: {r['problem']}")
            print(f"    - Treatment: {r['treatment_taken']}")
            print(f"    - Why Matched: {r['why_matched']}")

if __name__ == "__main__":
    run_tests()
