"""Shared LangGraph state for transcript analysis."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal

from typing_extensions import TypedDict

Strategy = Literal["single", "multi", "auto"]
Mode = Literal["meeting", "interview"]


class TranscriptState(TypedDict, total=False):
    session_id: str
    mode: Mode
    strategy: Strategy
    raw_transcript: str
    clean_text: str
    chunks: list[dict]
    segments: list[dict]
    meta: dict[str, Any]

    chunk_summaries: Annotated[list[dict], operator.add]
    partial_reviews: Annotated[list[dict], operator.add]

    merged_facts: dict | None
    final_output: dict | None
    validation_errors: list[str]

    interview_options: dict[str, Any]
    agent_trace: Annotated[list[dict], operator.add]
    token_budget_remaining: int

    # Per-worker payload (LangGraph Send)
    chunk: dict
    resolved_strategy: str
