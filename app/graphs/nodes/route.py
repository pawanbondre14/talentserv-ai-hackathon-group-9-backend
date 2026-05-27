"""Resolve processing strategy (single vs meeting / interview map-reduce)."""

from __future__ import annotations

import time
from typing import Any, Literal

from app.graphs.context import get_graph_settings
from app.graphs.state import TranscriptState

RouteTarget = Literal["single_shot", "meeting_graph", "interview_graph"]


def _has_panel_transcripts(state: TranscriptState) -> bool:
    opts = state.get("interview_options") or {}
    panels = opts.get("panel_transcripts") or []
    return bool(panels and len([p for p in panels if p and str(p).strip()]) > 0)


def resolve_route(state: TranscriptState) -> RouteTarget:
    settings = get_graph_settings()
    mode = state.get("mode") or "meeting"
    strategy = state.get("strategy") or "auto"
    meta = state.get("meta") or {}
    wc = meta.get("word_count") or 0
    chunks = state.get("chunks") or []

    if mode == "interview":
        if _has_panel_transcripts(state):
            return "single_shot"
        if strategy == "single":
            return "single_shot"
        if strategy == "multi":
            return "interview_graph"
        if wc >= settings.multi_word_threshold and len(chunks) > 1:
            return "interview_graph"
        return "single_shot"

    # meeting
    if strategy == "single":
        return "single_shot"
    if strategy == "multi":
        return "meeting_graph"
    if wc >= settings.multi_word_threshold and len(chunks) > 1:
        return "meeting_graph"
    return "single_shot"


def route_strategy_node(state: TranscriptState) -> dict[str, Any]:
    t0 = time.perf_counter()
    resolved = resolve_route(state)
    meta = dict(state.get("meta") or {})
    meta["resolved_strategy"] = resolved
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "resolved_strategy": resolved,
        "meta": meta,
        "agent_trace": [
            {
                "node": "route_strategy",
                "strategy": state.get("strategy") or "auto",
                "resolved_path": resolved,
                "latency_ms": elapsed_ms,
            }
        ],
    }


def route_after_strategy(state: TranscriptState) -> str:
    return resolve_route(state)
