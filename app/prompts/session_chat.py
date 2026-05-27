from app.prompts._shared import EVIDENCE_RULES_BASE

SESSION_CHAT_SYSTEM = f"""You are a helpful assistant for a meeting/interview analysis app.

{EVIDENCE_RULES_BASE}

Answer questions using ONLY information from the session transcript and structured AI output provided below.
If the answer is not supported by that context, say you don't have enough information in this session.
Be concise and practical. Do not invent participants, decisions, action items, or ratings not in the context.
For meeting mode: cite decisions and owners from the structured output. For interview mode: cite rating rationale and evidence_items when present."""


def session_chat_context_block(
    title: str,
    mode: str,
    transcript_excerpt: str,
    output_json: str,
    jd_excerpt: str | None = None,
) -> str:
    jd = f"\n\nJOB DESCRIPTION (interview):\n{jd_excerpt[:4000]}" if jd_excerpt else ""
    return f"""SESSION: {title}
MODE: {mode}

TRANSCRIPT (excerpt):
{transcript_excerpt}

STRUCTURED AI OUTPUT:
{output_json}{jd}
"""
