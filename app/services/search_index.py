import json
import re

from app.models import Output, SessionRecord

_HTML = re.compile(r"<[^>]+>")


def build_search_blob(session: SessionRecord, output: Output | None = None) -> str:
    parts = [session.title or "", session.transcript_text or ""]
    if output:
        payload = output.edited_json or output.ai_json
        if payload:
            try:
                parts.append(json.dumps(payload, ensure_ascii=False))
            except (TypeError, ValueError):
                parts.append(str(payload))
    return " ".join(parts).strip()


def extract_snippet(
    session: SessionRecord,
    output: Output | None = None,
    query: str | None = None,
    max_len: int = 160,
) -> str:
    candidates: list[str] = []
    if session.transcript_text:
        candidates.append(session.transcript_text)
    if output:
        data = output.edited_json or output.ai_json or {}
        if isinstance(data, dict):
            for key in ("executive_summary", "candidate_summary", "rationale"):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    candidates.append(val)
    text = candidates[0] if candidates else session.title or ""
    text = _HTML.sub(" ", text).strip()
    if not text:
        return "No preview available."

    if query and query.strip():
        q = query.strip().lower()
        lower = text.lower()
        idx = lower.find(q)
        if idx >= 0:
            start = max(0, idx - 50)
            excerpt = text[start : start + max_len]
            prefix = "…" if start > 0 else ""
            suffix = "…" if start + max_len < len(text) else ""
            return f"{prefix}{excerpt}{suffix}"

    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"
