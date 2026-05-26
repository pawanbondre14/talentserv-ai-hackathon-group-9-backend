import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import InterviewMeta, SessionRecord
from app.prompts.interview_feedback import INTERVIEW_FEEDBACK_SYSTEM, interview_feedback_prompt
from app.prompts.interview_jd import JD_ANALYSIS_SYSTEM, jd_analysis_prompt
from app.prompts.interview_panel import PANEL_MERGE_SYSTEM, panel_merge_prompt
from app.schemas.interview import InterviewProcessOptions
from app.services.interview_redact import redact_pii
from app.services.llm import complete_json
from app.services.scorecards import get_scorecard, scorecard_prompt_block

logger = logging.getLogger(__name__)


def _upsert_interview_meta(
    db: Session, session: SessionRecord, options: InterviewProcessOptions
) -> InterviewMeta:
    meta = session.interview_meta
    if not meta:
        meta = InterviewMeta(session_id=session.id)
        db.add(meta)
        session.interview_meta = meta
    meta.jd_text = options.jd_text
    meta.scorecard_id = options.scorecard_id
    meta.blind_mode = options.blind_mode
    meta.candidate_name = options.candidate_name
    meta.candidate_email = options.candidate_email
    db.commit()
    db.refresh(meta)
    return meta


def process_interview(
    settings: Settings,
    transcript: str,
    options: InterviewProcessOptions | None,
    session_id: str | None = None,
) -> dict[str, Any]:
    opts = options or InterviewProcessOptions()
    panels = [t.strip() for t in (opts.panel_transcripts or []) if t and t.strip()]
    scorecard_extra = ""
    if opts.scorecard_id:
        card = get_scorecard(opts.scorecard_id)
        if card:
            scorecard_extra = scorecard_prompt_block(card)
        else:
            logger.warning("Unknown scorecard_id=%s", opts.scorecard_id)

    if panels:
        logger.info("Panel merge: combining %d additional transcripts", len(panels))
        all_parts = [transcript.strip(), *panels]
        if opts.blind_mode:
            all_parts = [redact_pii(t) for t in all_parts]
        prompt = panel_merge_prompt(all_parts)
        if scorecard_extra:
            prompt += f"\n\n{scorecard_extra}"
        merged = complete_json(
            settings,
            PANEL_MERGE_SYSTEM,
            prompt,
            mode="interview",
            session_id=session_id,
        )
        return _maybe_jd_analysis(settings, merged, "\n\n".join(all_parts), opts, session_id)

    text = transcript.strip()
    if opts.blind_mode:
        logger.info("Blind review: redacting PII before LLM (session_id=%s)", session_id)
        text = redact_pii(text)

    result = complete_json(
        settings,
        INTERVIEW_FEEDBACK_SYSTEM,
        interview_feedback_prompt(text, scorecard_extra),
        mode="interview",
        session_id=session_id,
    )

    return _maybe_jd_analysis(settings, result, text, opts, session_id)


def _maybe_jd_analysis(
    settings: Settings,
    feedback: dict[str, Any],
    transcript: str,
    opts: InterviewProcessOptions,
    session_id: str | None,
) -> dict[str, Any]:
    if not opts.jd_text or not opts.jd_text.strip():
        feedback.pop("jd_analysis", None)
        return feedback

    logger.info("JD analysis pass (session_id=%s)", session_id)
    summary = feedback.get("candidate_summary", "")
    jd = complete_json(
        settings,
        JD_ANALYSIS_SYSTEM,
        jd_analysis_prompt(transcript, opts.jd_text.strip(), summary),
        mode="jd",
        session_id=session_id,
    )
    feedback["jd_analysis"] = jd
    return feedback


def apply_interview_post_hooks(
    settings: Settings,
    feedback: dict[str, Any],
    transcript: str,
    options: InterviewProcessOptions | None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """JD analysis and other post-graph interview steps."""
    opts = options or InterviewProcessOptions()
    return _maybe_jd_analysis(settings, feedback, transcript, opts, session_id)


def save_interview_meta_for_session(
    db: Session, session: SessionRecord, options: InterviewProcessOptions | None
) -> None:
    if session.mode != "interview" or not options:
        return
    _upsert_interview_meta(db, session, options)
