import json
import logging
import re
import time
from typing import Any

from fastapi import HTTPException

from app.config import Settings
from app.prompts.interview_feedback import INTERVIEW_FEEDBACK_SYSTEM, interview_feedback_prompt
from app.prompts.meeting_minutes import MEETING_MINUTES_SYSTEM, meeting_minutes_prompt

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

MODE_LABELS = {
    "meeting": "Meeting Minutes",
    "interview": "Interview Feedback",
    "jd": "JD Analysis",
    "chat": "Session Chat",
}


def _mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


def _strip_json_fences(text: str) -> str:
    t = text.strip()
    t = _JSON_FENCE.sub("", t).strip()
    return t


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = _strip_json_fences(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as inner:
                raise ValueError(f"Invalid JSON from model: {inner}") from exc
        else:
            raise ValueError(f"Invalid JSON from model: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object.")
    return data


def _log_output_summary(mode: str, data: dict[str, Any]) -> None:
    label = _mode_label(mode)
    if mode == "interview":
        rating = data.get("rating", "—")
        strengths = len(data.get("strengths") or [])
        concerns = len(data.get("concerns") or [])
        logger.info(
            "[%s] Response summary: rating=%s strengths=%d concerns=%d follow_ups=%d",
            label,
            rating,
            strengths,
            concerns,
            len(data.get("follow_up_questions") or []),
        )
    else:
        logger.info(
            "[%s] Response summary: decisions=%d action_items=%d risks=%d follow_ups=%d",
            label,
            len(data.get("decisions") or []),
            len(data.get("action_items") or []),
            len(data.get("risks") or []),
            len(data.get("follow_ups") or []),
        )


def _mock_meeting() -> dict[str, Any]:
    return {
        "executive_summary": "Team aligned on Q2 priorities and ownership for delivery.",
        "discussion_points": [
            {
                "topic": "Roadmap",
                "summary": "Discussed feature freeze date and scope.",
                "participants": ["Alex", "Jordan"],
            }
        ],
        "decisions": [
            {
                "decision": "Ship MVP by June 15",
                "rationale": "Customer commitments require early delivery.",
                "owner": "Alex",
            }
        ],
        "action_items": [
            {
                "task": "Finalize API spec",
                "owner": "Jordan",
                "due_date": "not specified",
                "priority": "High",
            }
        ],
        "risks": ["Capacity constraints on backend team"],
        "follow_ups": ["Review hiring plan next week"],
    }


def _mock_jd_analysis() -> dict[str, Any]:
    return {
        "overall_fit_score": 7,
        "matched_requirements": ["Python backend experience", "REST API design"],
        "gaps": ["Limited cloud-native architecture examples"],
        "summary": "Good fit for mid-level backend role with mentorship on distributed systems.",
    }


def _mock_interview() -> dict[str, Any]:
    return {
        "candidate_summary": "Strong communicator with solid fundamentals; some gaps in system design depth.",
        "skill_observations": {
            "technical_skills": "Comfortable with Python and REST APIs.",
            "communication": "Clear and structured answers.",
            "problem_solving": "Good approach on coding exercise.",
            "culture_fit": "Not assessed",
        },
        "strengths": ["Clear communication", "Practical debugging approach"],
        "concerns": ["Limited large-scale architecture examples"],
        "communication_assessment": "Professional and concise.",
        "rating": "Proceed",
        "rationale": "Meets bar for mid-level role with coaching on design.",
        "follow_up_questions": ["Describe a production incident you led end-to-end."],
        "qa_pairs": [
            {
                "question": "Walk me through a recent API you designed.",
                "answer": "Described REST resources and pagination approach.",
                "notes": "Solid fundamentals",
            },
            {
                "question": "How do you debug production issues?",
                "answer": "Structured logging and reproduction in staging.",
                "notes": "",
            },
        ],
        "scorecard_scores": [
            {"criterion": "Coding & debugging", "criterion_id": "coding", "score": 4, "notes": "Clear examples"},
            {"criterion": "System design", "criterion_id": "system_design", "score": 3, "notes": "Limited scale"},
            {"criterion": "API design & data modeling", "criterion_id": "api_design", "score": 4, "notes": ""},
        ],
    }


def _should_mock(settings: Settings) -> bool:
    if settings.llm_mock:
        return True
    if settings.llm_provider == "openai":
        return not settings.openai_api_key
    return not settings.anthropic_api_key


def _resolve_model(settings: Settings, model_tier: str = "strong") -> str:
    if settings.llm_provider == "openai":
        if model_tier == "fast":
            return settings.openai_model_fast or settings.openai_model
        return settings.openai_model
    return settings.anthropic_model


def _call_anthropic(
    settings: Settings,
    system: str,
    user_prompt: str,
    mode: str,
    model_tier: str = "strong",
) -> str:
    import anthropic

    model = _resolve_model(settings, model_tier)
    label = _mode_label(mode)
    logger.info(
        "[%s] Calling Anthropic model=%s tier=%s (prompt_chars=%d)",
        label,
        model,
        model_tier,
        len(user_prompt),
    )
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    parts = [block.text for block in message.content if hasattr(block, "text")]
    raw = "\n".join(parts)
    logger.info("[%s] Anthropic response received (chars=%d)", label, len(raw))
    return raw


def _call_openai(
    settings: Settings,
    system: str,
    user_prompt: str,
    mode: str,
    model_tier: str = "strong",
) -> str:
    from openai import OpenAI

    model = _resolve_model(settings, model_tier)
    label = _mode_label(mode)
    logger.info(
        "[%s] Calling OpenAI model=%s tier=%s (prompt_chars=%d)",
        label,
        model,
        model_tier,
        len(user_prompt),
    )
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or ""
    logger.info("[%s] OpenAI response received (chars=%d)", label, len(raw))
    return raw


def complete_json(
    settings: Settings,
    system: str,
    user_prompt: str,
    mode: str = "meeting",
    session_id: str | None = None,
    model_tier: str = "strong",
) -> dict[str, Any]:
    label = _mode_label(mode)
    sid = session_id or "—"
    started = time.perf_counter()

    if _should_mock(settings):
        logger.info(
            "[%s] Generating MOCK response (session_id=%s) — no live API call",
            label,
            sid,
        )
        if mode == "jd":
            data = _mock_jd_analysis()
        elif mode == "interview":
            data = _mock_interview()
        else:
            data = _mock_meeting()
        elapsed = time.perf_counter() - started
        logger.info(
            "[%s] MOCK generation complete (session_id=%s, elapsed=%.2fs)",
            label,
            sid,
            elapsed,
        )
        _log_output_summary(mode, data)
        return data

    provider = settings.llm_provider
    logger.info(
        "[%s] Starting LIVE AI generation (session_id=%s, provider=%s)",
        label,
        sid,
        provider,
    )

    raw = ""
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            if attempt > 0:
                logger.warning(
                    "[%s] Retrying AI call after invalid JSON (session_id=%s, attempt=%d)",
                    label,
                    sid,
                    attempt + 1,
                )
            if settings.llm_provider == "openai":
                if not settings.openai_api_key:
                    raise HTTPException(500, "OPENAI_API_KEY is not configured.")
                raw = _call_openai(settings, system, user_prompt, mode, model_tier)
            else:
                if not settings.anthropic_api_key:
                    raise HTTPException(500, "ANTHROPIC_API_KEY is not configured.")
                raw = _call_anthropic(settings, system, user_prompt, mode, model_tier)
            data = parse_json_response(raw)
            elapsed = time.perf_counter() - started
            logger.info(
                "[%s] LIVE generation SUCCESS (session_id=%s, provider=%s, elapsed=%.2fs)",
                label,
                sid,
                provider,
                elapsed,
            )
            _log_output_summary(mode, data)
            return data
        except HTTPException:
            elapsed = time.perf_counter() - started
            logger.error(
                "[%s] LIVE generation FAILED — HTTP error (session_id=%s, elapsed=%.2fs)",
                label,
                sid,
                elapsed,
            )
            raise
        except Exception as exc:
            last_error = exc
            logger.warning(
                "[%s] Parse/API error (session_id=%s): %s",
                label,
                sid,
                exc,
            )
            user_prompt = (
                user_prompt
                + "\n\nYour previous response was invalid JSON. Return ONLY a valid JSON object."
            )

    elapsed = time.perf_counter() - started
    logger.error(
        "[%s] LIVE generation FAILED after retries (session_id=%s, elapsed=%.2fs): %s",
        label,
        sid,
        elapsed,
        last_error,
    )
    raise HTTPException(
        status_code=502,
        detail=f"AI processing failed: {last_error}",
    ) from last_error


def _mock_chat_reply(user_message: str) -> str:
    preview = user_message.strip()[:120]
    return (
        f"Based on this session's transcript and AI output (mock): "
        f'"{preview}" — ask about action items, decisions, risks, or interview rating for more detail.'
    )


def _call_anthropic_chat(
    settings: Settings,
    system: str,
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    import anthropic

    messages: list[dict[str, str]] = []
    for turn in history[-20:]:
        role = turn.get("role")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=2048,
        system=system,
        messages=messages,
    )
    parts = [block.text for block in message.content if hasattr(block, "text")]
    return "\n".join(parts).strip()


def _call_openai_chat(
    settings: Settings,
    system: str,
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    from openai import OpenAI

    msgs: list[dict[str, str]] = [{"role": "system", "content": system}]
    for turn in history[-20:]:
        role = turn.get("role")
        if role in ("user", "assistant"):
            msgs.append({"role": role, "content": turn["content"]})
    msgs.append({"role": "user", "content": user_message})

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=msgs,
        max_tokens=2048,
    )
    return (response.choices[0].message.content or "").strip()


def complete_chat(
    settings: Settings,
    system: str,
    history: list[dict[str, str]],
    user_message: str,
    session_id: str | None = None,
) -> tuple[str, str]:
    """Returns (reply_text, provider)."""
    sid = session_id or "—"
    if _should_mock(settings):
        logger.info("[Session Chat] MOCK reply (session_id=%s)", sid)
        return _mock_chat_reply(user_message), "mock"

    provider = settings.llm_provider
    logger.info("[Session Chat] LIVE reply (session_id=%s, provider=%s)", sid, provider)
    try:
        if provider == "openai":
            if not settings.openai_api_key:
                raise HTTPException(500, "OPENAI_API_KEY is not configured.")
            raw = _call_openai_chat(settings, system, history, user_message)
        else:
            if not settings.anthropic_api_key:
                raise HTTPException(500, "ANTHROPIC_API_KEY is not configured.")
            raw = _call_anthropic_chat(settings, system, history, user_message)
        return raw or "I could not generate a reply.", provider
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[Session Chat] failed (session_id=%s): %s", sid, exc)
        raise HTTPException(status_code=502, detail=f"Chat failed: {exc}") from exc


def process_transcript(
    settings: Settings,
    mode: str,
    transcript: str,
    session_id: str | None = None,
    word_count: int | None = None,
) -> dict[str, Any]:
    label = _mode_label(mode)
    wc = word_count if word_count is not None else len(transcript.split())
    logger.info(
        "[%s] process_transcript invoked (session_id=%s, words=%d, chars=%d)",
        label,
        session_id or "—",
        wc,
        len(transcript),
    )

    if mode == "interview":
        from app.services.interview_processor import process_interview

        return process_interview(settings, transcript, None, session_id=session_id)
    return complete_json(
        settings,
        MEETING_MINUTES_SYSTEM,
        meeting_minutes_prompt(transcript),
        mode="meeting",
        session_id=session_id,
    )
