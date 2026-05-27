from app.prompts._shared import (
    INTERVIEW_ANALYSIS_STEPS,
    INTERVIEW_EVIDENCE_RULES,
    INTERVIEW_FINAL_JSON_SCHEMA,
    INTERVIEW_RATING_RUBRIC,
    INTERVIEW_SYNTHESIS_RATING_GUIDE,
    INTERVIEW_TRANSCRIPT_FORMAT_NOTE,
)

INTERVIEW_FEEDBACK_SYSTEM = f"""You are an experienced hiring manager. Extract interview feedback from transcripts only.

{INTERVIEW_EVIDENCE_RULES}

{INTERVIEW_RATING_RUBRIC}

{INTERVIEW_TRANSCRIPT_FORMAT_NOTE}"""


def interview_feedback_prompt(transcript: str, extra_instructions: str = "") -> str:
    extra = f"\n\n{extra_instructions}" if extra_instructions else ""
    return f"""Analyze this interview transcript and return JSON with exactly this structure:

{INTERVIEW_FINAL_JSON_SCHEMA}

{INTERVIEW_ANALYSIS_STEPS}

{INTERVIEW_SYNTHESIS_RATING_GUIDE}

Include qa_pairs for distinct Q&A exchanges found in the transcript.
Populate evidence_items with verbatim quotes for both strengths and concerns (include positive signals).
{extra}
TRANSCRIPT:
{transcript}
"""
