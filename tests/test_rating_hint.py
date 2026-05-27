"""Rating hint guard when specialist scores conflict with interviewer close."""

from app.graphs.interview.nodes import _rating_hint_from_reviews

PROCEED_CLOSE = (
    "Interviewer: Thank you. Based on today's discussion we'd like to proceed to the next round. "
    "You demonstrated strong ownership, practical technical depth, and good communication."
)


REJECT_CLOSE = (
    "Final Decision: Thank you. After review, we will not proceed further for this role."
)


def test_rating_hint_does_not_override_on_reject_close():
    reviews = [
        {"dimension": "technical", "score": 1},
        {"dimension": "communication", "score": 1},
    ]
    hint = _rating_hint_from_reviews(reviews, REJECT_CLOSE)
    assert "Reject" in hint
    assert "inconsistent" not in hint.lower()


def test_rating_hint_overrides_all_ones_when_interviewer_proceeds():
    reviews = [
        {"dimension": "technical", "score": 1},
        {"dimension": "communication", "score": 1},
        {"dimension": "culture", "score": 1},
    ]
    hint = _rating_hint_from_reviews(reviews, PROCEED_CLOSE)
    assert "Proceed" in hint
    assert "inconsistent" in hint.lower() or "prioritize" in hint.lower()
