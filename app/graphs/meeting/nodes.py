"""Meeting map-reduce LangGraph nodes (Phase B)."""

from __future__ import annotations

import json
import time
from typing import Any

from langgraph.types import Send

from app.graphs.context import get_graph_settings
from app.graphs.state import TranscriptState
from app.prompts.meeting_chunk import (
    CHUNK_SUMMARY_SYSTEM,
    MERGE_ACTIONS_SYSTEM,
    SYNTHESIZE_MINUTES_SYSTEM,
    chunk_summary_prompt,
    merge_actions_prompt,
    synthesize_minutes_prompt,
)
from app.services.llm import complete_json, _should_mock


def _mock_chunk_summary(chunk_id: str) -> dict[str, Any]:
    return {
        "chunk_id": chunk_id,
        "discussion_points": [
            {
                "topic": f"Sprint topic ({chunk_id})",
                "summary": "Team discussed deliverables and ownership.",
                "participants": ["Alex", "Jordan"],
            }
        ],
        "decisions": [
            {
                "decision": f"Proceed with milestone ({chunk_id})",
                "rationale": "Customer commitments require delivery.",
                "owner": "Alex",
            }
        ],
        "action_items": [
            {
                "task": f"Document API checklist ({chunk_id})",
                "owner": "Jordan",
                "due_date": "not specified",
                "priority": "High",
            }
        ],
        "risks": [f"Capacity risk noted in {chunk_id}"],
        "follow_ups": [f"Regression pass after {chunk_id}"],
    }


def begin_meeting_node(state: TranscriptState) -> dict[str, Any]:
    return {}


def map_summarize_chunks(state: TranscriptState) -> list[Send]:
    chunks = state.get("chunks") or []
    if not chunks:
        text = state.get("clean_text") or state.get("raw_transcript") or ""
        chunks = [{"chunk_id": "c_00", "text": text, "word_count": len(text.split())}]
    session_id = state.get("session_id") or ""
    return [
        Send("summarize_chunk", {"chunk": c, "session_id": session_id})
        for c in chunks
    ]


def summarize_chunk_node(state: TranscriptState) -> dict[str, Any]:
    settings = get_graph_settings()
    chunk = state.get("chunk") or {}
    chunk_id = chunk.get("chunk_id", "c_00")
    text = chunk.get("text", "")
    session_id = state.get("session_id")

    t0 = time.perf_counter()
    if _should_mock(settings):
        data = _mock_chunk_summary(chunk_id)
    else:
        data = complete_json(
            settings,
            CHUNK_SUMMARY_SYSTEM,
            chunk_summary_prompt(chunk_id, text),
            mode="meeting",
            session_id=session_id,
            model_tier="fast",
        )
        data.setdefault("chunk_id", chunk_id)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "chunk_summaries": [data],
        "agent_trace": [
            {
                "node": "summarize_chunk",
                "chunk_id": chunk_id,
                "latency_ms": elapsed_ms,
            }
        ],
    }


def link_entities_node(state: TranscriptState) -> dict[str, Any]:
    """Deterministic merge of chunk summaries (no LLM)."""
    t0 = time.perf_counter()
    summaries = state.get("chunk_summaries") or []
    discussion_points: list[dict] = []
    all_participants: set[str] = set()

    for summary in summaries:
        for dp in summary.get("discussion_points") or []:
            if isinstance(dp, dict):
                discussion_points.append(dp)
                for p in dp.get("participants") or []:
                    if p:
                        all_participants.add(str(p))

    merged = {
        "discussion_points": discussion_points,
        "participants": sorted(all_participants),
        "chunk_ids": [s.get("chunk_id") for s in summaries if s.get("chunk_id")],
        "raw_chunk_summaries": summaries,
    }
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "merged_facts": merged,
        "agent_trace": [
            {
                "node": "link_entities",
                "chunk_count": len(summaries),
                "participant_count": len(all_participants),
                "latency_ms": elapsed_ms,
            }
        ],
    }


def merge_actions_node(state: TranscriptState) -> dict[str, Any]:
    settings = get_graph_settings()
    merged = state.get("merged_facts") or {}
    summaries = merged.get("raw_chunk_summaries") or []
    session_id = state.get("session_id")

    outline = json.dumps(summaries, indent=2)[:120_000]
    t0 = time.perf_counter()

    if _should_mock(settings):
        deduped = {
            "decisions": [],
            "action_items": [],
            "risks": [],
            "follow_ups": [],
        }
        for s in summaries:
            deduped["decisions"].extend(s.get("decisions") or [])
            deduped["action_items"].extend(s.get("action_items") or [])
            deduped["risks"].extend(s.get("risks") or [])
            deduped["follow_ups"].extend(s.get("follow_ups") or [])
    else:
        deduped = complete_json(
            settings,
            MERGE_ACTIONS_SYSTEM,
            merge_actions_prompt(outline),
            mode="meeting",
            session_id=session_id,
            model_tier="strong",
        )

    merged = dict(merged)
    merged["deduped"] = deduped
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "merged_facts": merged,
        "agent_trace": [
            {
                "node": "merge_actions",
                "decisions": len(deduped.get("decisions") or []),
                "action_items": len(deduped.get("action_items") or []),
                "latency_ms": elapsed_ms,
            }
        ],
    }


def synthesize_minutes_node(state: TranscriptState) -> dict[str, Any]:
    settings = get_graph_settings()
    merged = state.get("merged_facts") or {}
    text = state.get("clean_text") or ""
    excerpt = text[:3000]
    session_id = state.get("session_id")
    facts_json = json.dumps(merged, indent=2)[:120_000]

    t0 = time.perf_counter()
    if _should_mock(settings):
        from app.services.llm import _mock_meeting

        output = _mock_meeting()
        output["executive_summary"] = (
            f"Multi-agent meeting synthesis across {len(merged.get('chunk_ids') or [])} chunks."
        )
    else:
        output = complete_json(
            settings,
            SYNTHESIZE_MINUTES_SYSTEM,
            synthesize_minutes_prompt(facts_json, excerpt),
            mode="meeting",
            session_id=session_id,
            model_tier="strong",
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "final_output": output,
        "agent_trace": [
            {
                "node": "synthesize_minutes",
                "resolved_path": "meeting_graph",
                "latency_ms": elapsed_ms,
            }
        ],
    }
