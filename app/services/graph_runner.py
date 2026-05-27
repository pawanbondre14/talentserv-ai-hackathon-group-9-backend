"""Invoke LangGraph transcript pipeline or fall back to legacy LLM services."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import HTTPException

from app.config import Settings
from app.graphs.context import reset_graph_settings, set_graph_settings
from app.schemas.interview import InterviewProcessOptions
from app.services.interview_processor import apply_interview_post_hooks, process_interview
from app.services.interview_redact import redact_pii
from app.services.llm import process_transcript

logger = logging.getLogger(__name__)

Strategy = Literal["single", "multi", "auto"]


def _legacy_run(
    settings: Settings,
    mode: str,
    transcript: str,
    session_id: str | None,
    interview_options: InterviewProcessOptions | None,
    word_count: int | None,
) -> dict[str, Any]:
    if mode == "interview":
        return process_interview(
            settings,
            transcript,
            interview_options,
            session_id=session_id,
        )
    return process_transcript(
        settings,
        mode,
        transcript,
        session_id=session_id,
        word_count=word_count,
    )


def _interview_options_dict(options: InterviewProcessOptions | None) -> dict[str, Any]:
    if not options:
        return {}
    return options.model_dump(exclude_none=True)


def _prepare_transcript(
    mode: str,
    transcript: str,
    interview_options: InterviewProcessOptions | None,
) -> str:
    if mode != "interview" or not interview_options or not interview_options.blind_mode:
        return transcript
    logger.info("Blind review: redacting PII before LangGraph")
    return redact_pii(transcript)


def run_analysis(
    settings: Settings,
    *,
    session_id: str,
    mode: str,
    transcript: str,
    interview_options: InterviewProcessOptions | None = None,
    strategy: Strategy = "auto",
    word_count: int | None = None,
    truncated: bool = False,
) -> dict[str, Any]:
    """
    Run transcript analysis. Uses LangGraph when settings.langgraph_enabled is True.
    Returns the same JSON shape as legacy process_transcript / process_interview.
    """
    if not settings.langgraph_enabled:
        return _legacy_run(
            settings,
            mode,
            transcript,
            session_id,
            interview_options,
            word_count,
        )

    text = _prepare_transcript(mode, transcript, interview_options)

    initial: dict[str, Any] = {
        "session_id": session_id,
        "mode": mode,
        "strategy": strategy,
        "raw_transcript": text,
        "interview_options": _interview_options_dict(interview_options),
        "meta": {
            "word_count": word_count,
            "truncated": truncated,
        },
        "agent_trace": [],
    }
    config = {"configurable": {"settings": settings}}

    logger.info(
        "LangGraph invoke | session_id=%s | mode=%s | strategy=%s",
        session_id,
        mode,
        strategy,
    )
    try:
        from app.graphs.parent import get_compiled_graph
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "LANGGRAPH_ENABLED=true but langgraph is not installed. "
                "Run: pip install -r requirements.txt"
            ),
        ) from exc

    token = set_graph_settings(settings)
    try:
        result = get_compiled_graph().invoke(initial, config)
    finally:
        reset_graph_settings(token)

    errors = result.get("validation_errors") or []
    if errors:
        logger.warning(
            "LangGraph validation warnings | session_id=%s | errors=%s",
            session_id,
            errors,
        )

    output = result.get("final_output")
    if not output or not isinstance(output, dict):
        raise HTTPException(
            status_code=502,
            detail="AI processing failed: graph did not produce final_output.",
        )

    if mode == "interview":
        output = apply_interview_post_hooks(
            settings,
            output,
            text,
            interview_options,
            session_id=session_id,
        )

    trace = result.get("agent_trace") or []
    if trace:
        logger.info(
            "LangGraph complete | session_id=%s | nodes=%s",
            session_id,
            [t.get("node") for t in trace],
        )

    return output
