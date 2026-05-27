"""Deterministic transcript preprocessing (no LLM)."""

from __future__ import annotations

import time
from typing import Any

from app.graphs.context import get_graph_settings
from app.graphs.state import TranscriptState
from app.services.chunking import chunk_transcript
from app.services.normalize import normalize_transcript, word_count


def preprocess_node(state: TranscriptState) -> dict[str, Any]:
    settings = get_graph_settings()
    raw = state.get("raw_transcript") or ""
    t0 = time.perf_counter()
    clean = normalize_transcript(raw)
    wc = word_count(clean)
    chunks = chunk_transcript(
        clean,
        max_words=settings.chunk_max_words,
        overlap_words=settings.chunk_overlap_words,
    )
    meta = dict(state.get("meta") or {})
    meta.setdefault("word_count", wc)
    meta.setdefault("char_count", len(clean))
    meta["chunk_count"] = len(chunks)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    return {
        "clean_text": clean,
        "chunks": chunks,
        "segments": [],
        "meta": meta,
        "agent_trace": [
            {
                "node": "preprocess",
                "word_count": wc,
                "chunk_count": len(chunks),
                "latency_ms": elapsed_ms,
            }
        ],
    }
