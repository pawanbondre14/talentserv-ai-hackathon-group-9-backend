"""Regression: extract_evidence must use 1-5 specialist scale, not 1-10."""

from app.graphs.interview.nodes import extract_evidence_node


def test_extract_evidence_treats_score_4_as_strength_not_concern():
    state = {
        "partial_reviews": [
            {
                "type": "dimension_review",
                "dimension": "technical",
                "score": 4,
                "summary": "Solid technical depth",
                "evidence_quotes": ["I designed the API with pagination."],
            },
            {
                "type": "dimension_review",
                "dimension": "communication",
                "score": 3,
                "summary": "Adequate clarity",
                "evidence_quotes": ["I explained the trade-offs clearly."],
            },
        ],
        "merged_facts": {},
    }
    result = extract_evidence_node(state)
    evidence = result["merged_facts"]["evidence"]
    assert any("technical" in s for s in evidence["strengths"])
    assert not any("technical" in c for c in evidence["concerns"])
    assert not any("communication" in c for c in evidence["concerns"])
