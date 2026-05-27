JD_ANALYSIS_SYSTEM = """You are a hiring manager. Compare interview evidence to a job description.
Return valid JSON only. Base scores on transcript evidence, not assumptions."""


def jd_analysis_prompt(transcript: str, jd_text: str, feedback_summary: str) -> str:
    return f"""Given the job description and interview transcript (and summary), return:

{{
  "overall_fit_score": 1-10,
  "matched_requirements": ["requirement met with evidence"],
  "gaps": ["requirement not demonstrated or weak"],
  "summary": "2-3 sentences on JD fit"
}}

JOB DESCRIPTION:
{jd_text}

INTERVIEW SUMMARY (from prior analysis):
{feedback_summary}

TRANSCRIPT EXCERPT (first 8000 chars):
{transcript[:8000]}
"""
