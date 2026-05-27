import re

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
_LINKEDIN = re.compile(r"\blinkedin\.com/in/[\w-]+\b", re.I)


def redact_pii(text: str) -> str:
    """Lightweight blind-review redaction before sending transcript to LLM."""
    out = _EMAIL.sub("[EMAIL]", text)
    out = _PHONE.sub("[PHONE]", out)
    out = _LINKEDIN.sub("[PROFILE]", out)
    # Common speaker labels — keep role-based labels, redact capitalized name patterns after colons
    out = re.sub(
        r"(?m)^((?:Interviewer|Candidate|Speaker)\s*\d*):\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
        r"\1: [REDACTED]",
        out,
    )
    return out
