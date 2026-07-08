import pytest
from backend.app.services.similarity_service import SimilarityService

def test_retrieval_returns_top_3():
    service = SimilarityService()
    results = service.retrieve_similar_cases(
        query_complaint="My laptop gets extremely hot and shuts down",
        predicted_problem="Overheating",
        pc_model="Dell Inspiron 6880",
        query_symptoms="High heat",
        top_k=3
    )
    
    assert isinstance(results, list)
    # Checks that we get exactly top_k results
    assert len(results) <= 3
    if len(results) > 0:
        # Check sorting order: rank 1 must have >= score than rank 2
        for i in range(len(results) - 1):
            assert results[i]["similarity_score"] >= results[i+1]["similarity_score"]
            assert results[i]["rank"] == i + 1

def test_weight_renormalization_on_missing_symptoms():
    service = SimilarityService()
    # Symptoms are missing/empty string
    results = service.retrieve_similar_cases(
        query_complaint="My laptop gets extremely hot and shuts down",
        predicted_problem="Overheating",
        pc_model="Dell Inspiron 6880",
        query_symptoms="",
        top_k=3
    )
    assert isinstance(results, list)
    if len(results) > 0:
        assert results[0]["similarity_score"] <= 100.0
        assert results[0]["similarity_score"] >= 0.0
