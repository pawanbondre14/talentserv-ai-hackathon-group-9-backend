import re

_HTML_TAG = re.compile(r"<[^>]+>")


def normalize_transcript(raw: str) -> str:
    text = raw or ""
    text = _HTML_TAG.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def word_count(text: str) -> int:
    if not text or not text.strip():
        return 0
    return len(text.split())


def truncate_transcript(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n\n[Transcript truncated for processing.]", True
