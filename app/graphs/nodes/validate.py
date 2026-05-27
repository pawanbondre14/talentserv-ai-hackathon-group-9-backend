"""Output schema validation (no LLM). Phase A: log errors; still pass output through."""

from __future__ import annotations

import time
from typing import Any

from app.graphs.state import TranscriptState

_MEETING_REQUIRED = (
    "executive_summary",
    "discussion_points",
    "decisions",
    "action_items",
    "risks",
    "follow_ups",
)

_INTERVIEW_REQUIRED = (
    "candidate_summary",
    "skill_observations",
    "strengths",
    "concerns",
    "rating",
    "rationale",
)

_VALID_RATINGS = frozenset({"Proceed", "Hold", "Reject"})


def _has_quote_field(item: dict) -> bool:
    for key in ("source_quote", "quote", "evidence_quote"):
        val = item.get(key)
        if val and str(val).strip():
            return True
    return False


def _validate_meeting(data: dict) -> list[str]:
    errors: list[str] = []
    for key in _MEETING_REQUIRED:
        if key not in data:
            errors.append(f"Missing required key: {key}")
    summary = data.get("executive_summary")
    if summary is not None and not str(summary).strip():
        errors.append("executive_summary is empty")

    for i, dec in enumerate(data.get("decisions") or []):
        if isinstance(dec, dict) and not _has_quote_field(dec):
            errors.append(f"decisions[{i}] missing source_quote (evidence)")

    for i, act in enumerate(data.get("action_items") or []):
        if isinstance(act, dict) and not _has_quote_field(act):
            errors.append(f"action_items[{i}] missing source_quote (evidence)")

    return errors


def _validate_interview(data: dict) -> list[str]:
    errors: list[str] = []
    for key in _INTERVIEW_REQUIRED:
        if key not in data:
            errors.append(f"Missing required key: {key}")
    rating = data.get("rating")
    if rating is not None and rating not in _VALID_RATINGS:
        errors.append(f"Invalid rating: {rating!r} (expected Proceed|Hold|Reject)")
    skills = data.get("skill_observations")
    if skills is not None and not isinstance(skills, dict):
        errors.append("skill_observations must be an object")

    evidence = data.get("evidence_items")
    strengths = data.get("strengths") or []
    concerns = data.get("concerns") or []
    if strengths or concerns:
        if not evidence and not (data.get("qa_pairs") or []):
            errors.append(
                "strengths/concerns present but no evidence_items or qa_pairs for grounding"
            )

    return errors


def validate_output_node(state: TranscriptState) -> dict[str, Any]:
    t0 = time.perf_counter()
    output = state.get("final_output")
    mode = state.get("mode") or "meeting"
    errors: list[str] = []

    if not output or not isinstance(output, dict):
        errors.append("final_output is missing or not a JSON object")
    elif mode == "interview":
        errors.extend(_validate_interview(output))
    else:
        errors.extend(_validate_meeting(output))

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "validation_errors": errors,
        "agent_trace": [
            {
                "node": "validate_output",
                "valid": len(errors) == 0,
                "error_count": len(errors),
                "latency_ms": elapsed_ms,
            }
        ],
    }
