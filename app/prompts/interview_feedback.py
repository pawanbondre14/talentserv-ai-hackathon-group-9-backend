INTERVIEW_FEEDBACK_SYSTEM = """You are an experienced hiring manager. Extract interview feedback from transcripts only.
Return valid JSON only — no markdown fences, no commentary.
Base ratings on transcript evidence. rating must be exactly one of: Proceed, Hold, Reject.
For skill areas not covered, use "Not assessed"."""


def interview_feedback_prompt(transcript: str) -> str:
    return f"""Analyze this interview transcript and return JSON with exactly these keys:

{{
  "candidate_summary": "2-3 sentences",
  "skill_observations": {{
    "technical_skills": "",
    "communication": "",
    "problem_solving": "",
    "culture_fit": ""
  }},
  "strengths": [],
  "concerns": [],
  "communication_assessment": "",
  "rating": "Proceed|Hold|Reject",
  "rationale": "",
  "follow_up_questions": []
}}

TRANSCRIPT:
{transcript}
"""
