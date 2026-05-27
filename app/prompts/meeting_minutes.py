from app.prompts._shared import (
    MEETING_ANALYSIS_STEPS,
    MEETING_EVIDENCE_RULES,
    MEETING_FINAL_JSON_SCHEMA,
)

MEETING_MINUTES_SYSTEM = f"""You are an expert meeting scribe. Extract structured meeting minutes from transcripts only.

{MEETING_EVIDENCE_RULES}"""


def meeting_minutes_prompt(transcript: str) -> str:
    return f"""Analyze this meeting transcript and return JSON with exactly this structure:

{MEETING_FINAL_JSON_SCHEMA}

{MEETING_ANALYSIS_STEPS}

TRANSCRIPT:
{transcript}
"""
