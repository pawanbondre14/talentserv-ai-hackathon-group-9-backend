from app.prompts._shared import (
    INTERVIEW_ANALYSIS_STEPS,
    INTERVIEW_EVIDENCE_RULES,
    INTERVIEW_FINAL_JSON_SCHEMA,
    INTERVIEW_RATING_RUBRIC,
)

PANEL_MERGE_SYSTEM = f"""You consolidate multiple interviewer notes/transcripts into one hiring feedback report.

{INTERVIEW_EVIDENCE_RULES}

{INTERVIEW_RATING_RUBRIC}

Note disagreements in concerns or rationale when interviewers differ.
Return valid JSON only."""


def panel_merge_prompt(transcripts: list[str]) -> str:
    parts = []
    for i, t in enumerate(transcripts, 1):
        parts.append(f"--- INTERVIEWER {i} ---\n{t.strip()}\n")
    combined = "\n".join(parts)
    schema = INTERVIEW_FINAL_JSON_SCHEMA.rstrip()
    if schema.endswith("}"):
        schema = schema[:-1] + ',\n  "panel_notes": "brief note on consensus vs dissent"\n}'
    return f"""Merge these interviewer transcripts into ONE consolidated feedback JSON:

{schema}

{INTERVIEW_ANALYSIS_STEPS}

Populate evidence_items from quotes across all interviewer transcripts.

{combined}
"""
