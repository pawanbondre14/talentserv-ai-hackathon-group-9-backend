"""Interview map-reduce + parallel reviewer nodes (Phase C)."""

from __future__ import annotations

import json
import time
from typing import Any

from langgraph.types import Send

from app.graphs.context import get_graph_settings
from app.graphs.state import TranscriptState
from app.prompts.interview_chunk import (
    CLASSIFY_CHUNK_SYSTEM,
    FAIRNESS_CHECK_SYSTEM,
    REVIEW_COMMUNICATION_SYSTEM,
    REVIEW_CULTURE_SYSTEM,
    REVIEW_TECHNICAL_SYSTEM,
    SYNTHESIZE_HIRING_SYSTEM,
    classify_chunk_prompt,
    fairness_check_prompt,
    review_communication_prompt,
    review_culture_prompt,
    review_technical_prompt,
    synthesize_hiring_prompt,
)
from app.services.llm import _mock_interview, _should_mock, complete_json
from app.services.scorecards import get_scorecard, scorecard_prompt_block


def _classifications_text(state: TranscriptState) -> str:
    merged = state.get("merged_facts") or {}
    return json.dumps(merged.get("classifications") or [], indent=2)[:80_000]


def _reviews_text(state: TranscriptState) -> str:
    reviews = [
        p for p in (state.get("partial_reviews") or []) if p.get("type") == "dimension_review"
    ]
    return json.dumps(reviews, indent=2)[:120_000]


def _scorecard_extra(state: TranscriptState) -> str:
    opts_raw = state.get("interview_options") or {}
    scorecard_id = opts_raw.get("scorecard_id")
    if not scorecard_id:
        return ""
    card = get_scorecard(scorecard_id)
    return scorecard_prompt_block(card) if card else ""


def begin_interview_node(state: TranscriptState) -> dict[str, Any]:
    return {}


def map_classify_chunks(state: TranscriptState) -> list[Send]:
    chunks = state.get("chunks") or []
    if not chunks:
        text = state.get("clean_text") or state.get("raw_transcript") or ""
        chunks = [{"chunk_id": "c_00", "text": text, "word_count": len(text.split())}]
    session_id = state.get("session_id") or ""
    return [
        Send("classify_chunk", {"chunk": c, "session_id": session_id})
        for c in chunks
    ]


def classify_chunk_node(state: TranscriptState) -> dict[str, Any]:
    settings = get_graph_settings()
    chunk = state.get("chunk") or {}
    chunk_id = chunk.get("chunk_id", "c_00")
    text = chunk.get("text", "")
    session_id = state.get("session_id")

    t0 = time.perf_counter()
    if _should_mock(settings):
        data = {
            "chunk_id": chunk_id,
            "segment_types": ["technical", "behavioral"],
            "has_technical_content": True,
            "has_communication_signals": True,
            "has_culture_fit_signals": True,
            "summary": f"Mock classification for {chunk_id}",
        }
    else:
        data = complete_json(
            settings,
            CLASSIFY_CHUNK_SYSTEM,
            classify_chunk_prompt(chunk_id, text),
            mode="interview",
            session_id=session_id,
            model_tier="fast",
        )
        data.setdefault("chunk_id", chunk_id)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "partial_reviews": [{"type": "classification", **data}],
        "agent_trace": [
            {"node": "classify_chunk", "chunk_id": chunk_id, "latency_ms": elapsed_ms},
        ],
    }


def aggregate_classifications_node(state: TranscriptState) -> dict[str, Any]:
    t0 = time.perf_counter()
    classifications = [
        p for p in (state.get("partial_reviews") or []) if p.get("type") == "classification"
    ]
    merged = dict(state.get("merged_facts") or {})
    merged["classifications"] = classifications
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "merged_facts": merged,
        "agent_trace": [
            {
                "node": "aggregate_classifications",
                "chunk_count": len(classifications),
                "latency_ms": elapsed_ms,
            }
        ],
    }


def map_review_dimensions(state: TranscriptState) -> list[Send]:
    session_id = state.get("session_id") or ""
    return [
        Send("review_technical", {"session_id": session_id}),
        Send("review_communication", {"session_id": session_id}),
        Send("review_culture", {"session_id": session_id}),
    ]


def _review_dimension(
    state: TranscriptState,
    dimension: str,
    system: str,
    prompt_fn,
) -> dict[str, Any]:
    settings = get_graph_settings()
    excerpt = (state.get("clean_text") or "")[:12_000]
    classifications = _classifications_text(state)
    session_id = state.get("session_id")

    t0 = time.perf_counter()
    if _should_mock(settings):
        data: dict[str, Any] = {
            "type": "dimension_review",
            "dimension": dimension,
            "score": 7,
            "summary": f"Mock {dimension} review",
            "evidence_quotes": ["Candidate gave a structured answer with examples."],
        }
        if dimension == "technical":
            data.update(
                technical_skills=["Python", "API design"],
                problem_solving="Solid structured approach",
                gaps=["Limited multi-region experience"],
            )
        elif dimension == "communication":
            data.update(clarity="Clear", structure="Well organized", red_flags=[])
        else:
            data.update(enthusiasm="High", collaboration_signals=["Team-oriented examples"], concerns=[])
    else:
        data = complete_json(
            settings,
            system,
            prompt_fn(excerpt, classifications),
            mode="interview",
            session_id=session_id,
            model_tier="fast",
        )
        data["type"] = "dimension_review"
        data["dimension"] = dimension

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "partial_reviews": [data],
        "agent_trace": [
            {"node": f"review_{dimension}", "latency_ms": elapsed_ms},
        ],
    }


def review_technical_node(state: TranscriptState) -> dict[str, Any]:
    return _review_dimension(
        state, "technical", REVIEW_TECHNICAL_SYSTEM, review_technical_prompt
    )


def review_communication_node(state: TranscriptState) -> dict[str, Any]:
    return _review_dimension(
        state, "communication", REVIEW_COMMUNICATION_SYSTEM, review_communication_prompt
    )


def review_culture_node(state: TranscriptState) -> dict[str, Any]:
    return _review_dimension(
        state, "culture", REVIEW_CULTURE_SYSTEM, review_culture_prompt
    )


def extract_evidence_node(state: TranscriptState) -> dict[str, Any]:
    """Collect quotes and strengths/concerns from dimension reviews."""
    t0 = time.perf_counter()
    reviews = [
        p for p in (state.get("partial_reviews") or []) if p.get("type") == "dimension_review"
    ]
    quotes: list[str] = []
    strengths: list[str] = []
    concerns: list[str] = []

    for rev in reviews:
        for q in rev.get("evidence_quotes") or []:
            if q and q not in quotes:
                quotes.append(str(q))
        summary = rev.get("summary") or ""
        dim = rev.get("dimension", "unknown")
        score = rev.get("score", 0)
        if isinstance(score, (int, float)) and score >= 6:
            strengths.append(f"{dim}: {summary}".strip())
        elif isinstance(score, (int, float)) and score <= 4:
            concerns.append(f"{dim}: {summary}".strip())
        for g in rev.get("gaps") or []:
            concerns.append(f"technical gap: {g}")
        for r in rev.get("red_flags") or []:
            concerns.append(f"communication: {r}")

    merged = dict(state.get("merged_facts") or {})
    merged["evidence"] = {
        "quotes": quotes[:30],
        "strengths": strengths[:15],
        "concerns": concerns[:15],
        "reviews": reviews,
    }
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "merged_facts": merged,
        "agent_trace": [
            {
                "node": "extract_evidence",
                "quote_count": len(quotes),
                "latency_ms": elapsed_ms,
            }
        ],
    }


def synthesize_hiring_node(state: TranscriptState) -> dict[str, Any]:
    settings = get_graph_settings()
    session_id = state.get("session_id")
    excerpt = (state.get("clean_text") or "")[:8000]
    reviews_json = _reviews_text(state)
    extra = _scorecard_extra(state)

    t0 = time.perf_counter()
    if _should_mock(settings):
        output = _mock_interview()
        output["candidate_summary"] = (
            "Multi-agent interview synthesis across specialist reviewers (mock)."
        )
    else:
        output = complete_json(
            settings,
            SYNTHESIZE_HIRING_SYSTEM,
            synthesize_hiring_prompt(reviews_json, excerpt, extra),
            mode="interview",
            session_id=session_id,
            model_tier="strong",
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "final_output": output,
        "agent_trace": [
            {
                "node": "synthesize_hiring",
                "resolved_path": "interview_graph",
                "latency_ms": elapsed_ms,
            }
        ],
    }


def fairness_check_node(state: TranscriptState) -> dict[str, Any]:
    settings = get_graph_settings()
    output = dict(state.get("final_output") or {})
    session_id = state.get("session_id")

    t0 = time.perf_counter()
    if _should_mock(settings):
        flags: list[str] = []
    else:
        check = complete_json(
            settings,
            FAIRNESS_CHECK_SYSTEM,
            fairness_check_prompt(json.dumps(output, indent=2)[:60_000]),
            mode="interview",
            session_id=session_id,
            model_tier="fast",
        )
        flags = check.get("flags") or []
        adjusted = check.get("adjusted_rating")
        if adjusted in ("Proceed", "Hold", "Reject"):
            output["rating"] = adjusted
        if flags:
            notes = check.get("notes") or ""
            output["rationale"] = (output.get("rationale") or "") + f" Fairness notes: {notes}"

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "final_output": output,
        "agent_trace": [
            {
                "node": "fairness_check",
                "flag_count": len(flags),
                "latency_ms": elapsed_ms,
            }
        ],
    }
