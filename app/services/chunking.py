"""Deterministic transcript chunking for map-reduce pipelines."""

from __future__ import annotations


def chunk_transcript(
    text: str,
    *,
    max_words: int = 800,
    overlap_words: int = 100,
) -> list[dict]:
    """Split text into overlapping word chunks for parallel LLM workers."""
    clean = (text or "").strip()
    if not clean:
        return []

    words = clean.split()
    total = len(words)
    if total <= max_words:
        return [
            {
                "chunk_id": "c_00",
                "text": clean,
                "word_count": total,
                "token_estimate": int(total * 1.3),
            }
        ]

    chunks: list[dict] = []
    start = 0
    idx = 0
    step = max(max_words - overlap_words, 1)

    while start < total:
        end = min(start + max_words, total)
        piece = " ".join(words[start:end])
        chunks.append(
            {
                "chunk_id": f"c_{idx:02d}",
                "text": piece,
                "word_count": end - start,
                "token_estimate": int((end - start) * 1.3),
            }
        )
        if end >= total:
            break
        start += step
        idx += 1

    return chunks


def estimate_tokens(word_count: int) -> int:
    return int(word_count * 1.3)
