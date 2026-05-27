PANEL_MERGE_SYSTEM = """You consolidate multiple interviewer notes/transcripts into one hiring feedback report.
Return valid JSON only. Note disagreements in concerns or rationale when interviewers differ."""


def panel_merge_prompt(transcripts: list[str]) -> str:
    parts = []
    for i, t in enumerate(transcripts, 1):
        parts.append(f"--- INTERVIEWER {i} ---\n{t.strip()}\n")
    combined = "\n".join(parts)
    return f"""Merge these interviewer transcripts into ONE consolidated feedback JSON with keys:

{{
  "candidate_summary": "",
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
  "rationale": "include any interviewer disagreement",
  "follow_up_questions": [],
  "qa_pairs": [{{"question": "", "answer": "", "notes": ""}}],
  "panel_notes": "brief note on consensus vs dissent"
}}

{combined}
"""
