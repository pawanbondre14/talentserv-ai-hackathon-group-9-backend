INTERVIEW_FEEDBACK_SYSTEM = """You are an experienced hiring manager. Extract interview feedback from transcripts only.
Return valid JSON only — no markdown fences, no commentary.
Base ratings on transcript evidence. rating must be exactly one of: Proceed, Hold, Reject.
For skill areas not covered, use "Not assessed"."""


def interview_feedback_prompt(transcript: str, extra_instructions: str = "") -> str:
    extra = f"\n\n{extra_instructions}" if extra_instructions else ""
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
  "follow_up_questions": [],
  "qa_pairs": [
    {{"question": "interviewer question", "answer": "candidate answer summary", "notes": ""}}
  ],
  "scorecard_scores": []
}}

Include qa_pairs for distinct Q&A exchanges found in the transcript.
{extra}
TRANSCRIPT:
{transcript}
"""
