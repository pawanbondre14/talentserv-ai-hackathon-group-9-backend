import re

_TIMESTAMP = re.compile(
    r"^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\s*$"
)
_INDEX = re.compile(r"^\d+$")
_HEADER = re.compile(r"^WEBVTT", re.I)


def vtt_to_plain_text(vtt: str) -> str:
    lines: list[str] = []
    for raw in vtt.splitlines():
        line = raw.strip()
        if not line or _HEADER.match(line) or _INDEX.match(line) or _TIMESTAMP.match(line):
            continue
        if line.upper() in ("NOTE", "STYLE", "REGION"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()
