"""Build chunk-filtered transcript excerpts for specialist reviewers."""

from __future__ import annotations

from typing import Any

_FLAG_BY_DIMENSION = {
    "technical": "has_technical_content",
    "communication": "has_communication_signals",
    "culture": "has_culture_fit_signals",
}


def _chunk_text_map(chunks: list[dict[str, Any]]) -> dict[str, str]:
    return {str(c.get("chunk_id", "")): c.get("text", "") for c in chunks if c.get("chunk_id")}


def build_dimension_excerpt(
    classifications: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    dimension: str,
    *,
    max_chars: int = 24_000,
    fallback_text: str = "",
    word_count: int | None = None,
) -> str:
    """Concatenate chunk texts relevant to a dimension; fallback to full transcript."""
    # Short interviews: always use full text so reviewers see closing interviewer signals.
    if word_count is not None and word_count < 3500:
        return (fallback_text or "")[:max_chars]

    flag = _FLAG_BY_DIMENSION.get(dimension)
    if not flag or not classifications:
        return (fallback_text or "")[:max_chars]

    text_by_id = _chunk_text_map(chunks)
    parts: list[str] = []
    total = 0

    for clf in classifications:
        if not clf.get(flag):
            continue
        cid = str(clf.get("chunk_id", ""))
        text = text_by_id.get(cid) or ""
        if not text.strip():
            continue
        block = f"--- CHUNK {cid} ---\n{text.strip()}\n"
        if total + len(block) > max_chars:
            remaining = max_chars - total
            if remaining > 200:
                parts.append(block[:remaining])
            break
        parts.append(block)
        total += len(block)

    if parts:
        return "\n".join(parts)
    return (fallback_text or "")[:max_chars]
