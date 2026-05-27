"""Fairness check must not change rating without flags."""

from unittest.mock import patch

import pytest

from app.config import Settings
from app.services.interview_fairness import apply_fairness_check


@pytest.fixture
def live_settings():
    s = Settings()
    s.llm_mock = False
    return s


def test_fairness_keeps_rating_when_no_flags(live_settings: Settings):
    feedback = {"rating": "Proceed", "rationale": "Strong candidate", "strengths": ["Clear answers"]}
    with patch("app.services.interview_fairness.complete_json") as mock_complete:
        mock_complete.return_value = {
            "flags": [],
            "adjusted_rating": "Reject",
            "notes": "",
        }
        out = apply_fairness_check(live_settings, feedback, session_id="t1")
    assert out["rating"] == "Proceed"


def test_fairness_applies_rating_when_flags_present(live_settings: Settings):
    feedback = {"rating": "Proceed", "rationale": "x", "strengths": []}
    with patch("app.services.interview_fairness.complete_json") as mock_complete:
        mock_complete.return_value = {
            "flags": ["Unsupported claim about degree"],
            "adjusted_rating": "Hold",
            "notes": "Downgraded",
        }
        out = apply_fairness_check(live_settings, feedback, session_id="t2")
    assert out["rating"] == "Hold"
    assert out.get("fairness_flags")
