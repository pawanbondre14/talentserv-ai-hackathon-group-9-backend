from app.prompts._shared import INTERVIEW_EVIDENCE_RULES

JD_ANALYSIS_SYSTEM = f"""You are a hiring manager. Compare interview evidence to a job description.

{INTERVIEW_EVIDENCE_RULES}

Base scores on transcript evidence, not assumptions.
Return valid JSON only."""


def jd_analysis_prompt(transcript: str, jd_text: str, feedback_summary: str) -> str:
    return f"""Given the job description and interview transcript (and summary), return:

{{
  "overall_fit_score": 1,
  "matched_requirements": ["requirement met with evidence quote"],
  "gaps": ["requirement not demonstrated or weak — cite what was missing"],
  "summary": "2-3 sentences on JD fit",
  "confidence": "high|medium|low"
}}

Map each matched_requirement and gap to explicit transcript evidence when possible.

JOB DESCRIPTION:
{jd_text}

INTERVIEW SUMMARY (from prior analysis):
{feedback_summary}

TRANSCRIPT EXCERPT (first 8000 chars):
{transcript[:8000]}
"""
