"""Single LLM call — same behavior as legacy process_transcript / process_interview."""

from __future__ import annotations

import time
from typing import Any

from app.graphs.state import TranscriptState
from app.prompts.meeting_minutes import MEETING_MINUTES_SYSTEM, meeting_minutes_prompt
from app.schemas.interview import InterviewProcessOptions
from app.graphs.context import get_graph_settings
from app.services.interview_processor import process_interview
from app.services.llm import complete_json


def single_shot_node(state: TranscriptState) -> dict[str, Any]:
    settings = get_graph_settings()
    text = state.get("clean_text") or state.get("raw_transcript") or ""
    mode = state.get("mode") or "meeting"
    session_id = state.get("session_id")
    strategy = state.get("strategy") or "auto"
    meta = state.get("meta") or {}
    wc = meta.get("word_count")

    t0 = time.perf_counter()
    if mode == "interview":
        opts_raw = state.get("interview_options") or {}
        options = InterviewProcessOptions.model_validate(opts_raw) if opts_raw else None
        output = process_interview(
            settings,
            text,
            options,
            session_id=session_id,
        )
    else:
        output = complete_json(
            settings,
            MEETING_MINUTES_SYSTEM,
            meeting_minutes_prompt(text),
            mode="meeting",
            session_id=session_id,
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "final_output": output,
        "agent_trace": [
            {
                "node": "single_shot",
                "mode": mode,
                "strategy": strategy,
                "resolved_path": "single",
                "latency_ms": elapsed_ms,
                "word_count": wc,
            }
        ],
    }
