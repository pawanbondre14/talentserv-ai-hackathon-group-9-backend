"""Tests for chunk-filtered interview reviewer context."""

from app.services.interview_context import build_dimension_excerpt


def test_build_dimension_excerpt_filters_by_flag():
    chunks = [
        {"chunk_id": "c_00", "text": "Technical API design discussion."},
        {"chunk_id": "c_01", "text": "Culture and team collaboration chat."},
    ]
    classifications = [
        {
            "chunk_id": "c_00",
            "has_technical_content": True,
            "has_communication_signals": False,
            "has_culture_fit_signals": False,
        },
        {
            "chunk_id": "c_01",
            "has_technical_content": False,
            "has_communication_signals": False,
            "has_culture_fit_signals": True,
        },
    ]
    tech = build_dimension_excerpt(classifications, chunks, "technical")
    culture = build_dimension_excerpt(classifications, chunks, "culture")

    assert "API design" in tech
    assert "collaboration" not in tech
    assert "collaboration" in culture
    assert "API design" not in culture


def test_build_dimension_excerpt_fallback_when_no_match():
    excerpt = build_dimension_excerpt([], [], "technical", fallback_text="Full transcript here.")
    assert excerpt == "Full transcript here."


def test_build_dimension_excerpt_uses_full_text_for_short_interviews():
    chunks = [{"chunk_id": "c_00", "text": "chunk only"}]
    classifications = [
        {
            "chunk_id": "c_00",
            "has_technical_content": True,
            "has_communication_signals": False,
            "has_culture_fit_signals": False,
        }
    ]
    excerpt = build_dimension_excerpt(
        classifications,
        chunks,
        "technical",
        fallback_text="Full transcript with closing proceed signal.",
        word_count=2000,
    )
    assert "Full transcript with closing" in excerpt
    assert "chunk only" not in excerpt
