"""Token budget guard before LLM fan-out."""

from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException

from app.graphs.context import get_graph_settings
from app.graphs.state import TranscriptState
from app.services.chunking import estimate_tokens


def budget_check_node(state: TranscriptState) -> dict[str, Any]:
    settings = get_graph_settings()
    meta = dict(state.get("meta") or {})
    wc = meta.get("word_count") or 0
    chunks = state.get("chunks") or []
    estimated = estimate_tokens(wc) + len(chunks) * 500
    remaining = settings.max_token_budget - estimated

    if estimated > settings.max_token_budget:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Transcript exceeds token budget (estimated {estimated}, "
                f"max {settings.max_token_budget}). Shorten the transcript or use single strategy."
            ),
        )

    t0 = time.perf_counter()
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "token_budget_remaining": remaining,
        "agent_trace": [
            {
                "node": "budget_check",
                "estimated_tokens": estimated,
                "token_budget_remaining": remaining,
                "latency_ms": elapsed_ms,
            }
        ],
    }
