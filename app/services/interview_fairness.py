"""Post-processing fairness check for interview feedback (all paths)."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import Settings
from app.prompts.interview_chunk import FAIRNESS_CHECK_SYSTEM, fairness_check_prompt
from app.services.llm import _should_mock, complete_json

logger = logging.getLogger(__name__)


def apply_fairness_check(
    settings: Settings,
    feedback: dict[str, Any],
    session_id: str | None = None,
) -> dict[str, Any]:
    """Run fairness review; adjust rating and append notes when flags exist."""
    output = dict(feedback)
    if _should_mock(settings):
        output["_fairness_checked"] = True
        return output

    try:
        check = complete_json(
            settings,
            FAIRNESS_CHECK_SYSTEM,
            fairness_check_prompt(json.dumps(output, indent=2)[:60_000]),
            mode="interview",
            session_id=session_id,
            model_tier="fast",
        )
    except Exception as exc:
        logger.warning("Fairness check skipped (session_id=%s): %s", session_id, exc)
        return output

    flags = check.get("flags") or []
    adjusted = check.get("adjusted_rating")
    original = output.get("rating")
    if flags and adjusted in ("Proceed", "Hold", "Reject"):
        output["rating"] = adjusted
    elif not flags and adjusted in ("Proceed", "Hold", "Reject") and adjusted != original:
        logger.info(
            "Fairness check ignored rating change without flags: %s -> %s",
            original,
            adjusted,
        )
    if flags:
        notes = check.get("notes") or ""
        output["rationale"] = (output.get("rationale") or "") + f" Fairness notes: {notes}"
        output["fairness_flags"] = flags
    output["_fairness_checked"] = True
    return output
