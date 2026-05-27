from app.prompts._shared import (
    INTERVIEW_ANALYSIS_STEPS,
    INTERVIEW_EVIDENCE_RULES,
    INTERVIEW_FINAL_JSON_SCHEMA,
    INTERVIEW_RATING_RUBRIC,
    INTERVIEW_SYNTHESIS_RATING_GUIDE,
    INTERVIEW_TRANSCRIPT_FORMAT_NOTE,
    SCORE_FIELD_INSTRUCTION,
    SCORE_SCALE_RUBRIC,
)

CLASSIFY_CHUNK_SYSTEM = f"""You classify interview transcript segments for downstream specialist reviewers.

{INTERVIEW_EVIDENCE_RULES}

Return valid JSON only."""


def classify_chunk_prompt(chunk_id: str, chunk_text: str) -> str:
    return f"""Classify this interview transcript segment (chunk {chunk_id}).

Return JSON:
{{
  "chunk_id": "{chunk_id}",
  "speakers": ["names or Interviewer/Candidate if unclear"],
  "topics": ["main topics discussed"],
  "questions_asked": ["interviewer questions in this segment"],
  "candidate_claims": ["factual claims the candidate made"],
  "segment_types": ["technical", "behavioral", "culture"],
  "has_technical_content": true,
  "has_communication_signals": true,
  "has_culture_fit_signals": true,
  "key_quotes": [{{"speaker": "", "quote": ""}}],
  "summary": "one sentence"
}}

SEGMENT:
{chunk_text}
"""


REVIEW_TECHNICAL_SYSTEM = f"""You evaluate technical skills and problem-solving from interview evidence only.

{INTERVIEW_EVIDENCE_RULES}

{INTERVIEW_TRANSCRIPT_FORMAT_NOTE}

{SCORE_SCALE_RUBRIC}

{SCORE_FIELD_INSTRUCTION}

Focus on technical depth, correctness, tradeoffs, and ownership. Do not score communication style here.
Return valid JSON only."""


def review_technical_prompt(transcript_excerpt: str, classifications: str) -> str:
    return f"""Review technical depth for this interview. Return JSON:
{{
  "dimension": "technical",
  "technical_skills": ["skills demonstrated with evidence"],
  "problem_solving": "assessment with evidence",
  "gaps": ["gaps with evidence or Not assessed"],
  "score": 4,
  "confidence": "high|medium|low",
  "evidence_quotes": ["exact quote from transcript"],
  "not_assessed": ["topics not covered in excerpt"],
  "summary": "brief evidence-based summary"
}}

CLASSIFICATIONS (chunk summaries — use to locate relevant segments):
{classifications}

TRANSCRIPT EXCERPT (relevant segments only):
{transcript_excerpt}
"""


REVIEW_COMMUNICATION_SYSTEM = f"""You evaluate communication quality from interview evidence only.

{INTERVIEW_EVIDENCE_RULES}

{INTERVIEW_TRANSCRIPT_FORMAT_NOTE}

{SCORE_SCALE_RUBRIC}

{SCORE_FIELD_INSTRUCTION}

Focus on clarity, structure, listening, and professionalism. Do not score technical depth here.
Return valid JSON only."""


def review_communication_prompt(transcript_excerpt: str, classifications: str) -> str:
    return f"""Review communication for this interview. Return JSON:
{{
  "dimension": "communication",
  "clarity": "assessment",
  "structure": "assessment",
  "red_flags": [],
  "score": 4,
  "confidence": "high|medium|low",
  "evidence_quotes": ["exact quote"],
  "not_assessed": [],
  "summary": "brief"
}}

CLASSIFICATIONS:
{classifications}

TRANSCRIPT EXCERPT:
{transcript_excerpt}
"""


REVIEW_CULTURE_SYSTEM = f"""You evaluate culture fit and motivation signals from interview evidence only.

{INTERVIEW_EVIDENCE_RULES}

{INTERVIEW_TRANSCRIPT_FORMAT_NOTE}

{SCORE_SCALE_RUBRIC}

{SCORE_FIELD_INSTRUCTION}

Focus on collaboration, values alignment, enthusiasm, and teamwork examples. Do not score technical skills here.
Return valid JSON only."""


def review_culture_prompt(transcript_excerpt: str, classifications: str) -> str:
    return f"""Review culture fit for this interview. Return JSON:
{{
  "dimension": "culture",
  "enthusiasm": "assessment",
  "collaboration_signals": ["signal with evidence"],
  "concerns": [],
  "score": 4,
  "confidence": "high|medium|low",
  "evidence_quotes": ["exact quote"],
  "not_assessed": [],
  "summary": "brief"
}}

CLASSIFICATIONS:
{classifications}

TRANSCRIPT EXCERPT:
{transcript_excerpt}
"""


SYNTHESIZE_HIRING_SYSTEM = f"""You synthesize specialist interview reviews into hiring feedback for recruiters.

{INTERVIEW_TRANSCRIPT_FORMAT_NOTE}

{INTERVIEW_EVIDENCE_RULES}

{INTERVIEW_RATING_RUBRIC}

Return valid JSON only."""


def synthesize_hiring_prompt(
    reviews_json: str,
    transcript_excerpt: str,
    extra_instructions: str = "",
    evidence_json: str = "",
) -> str:
    extra = f"\n\n{extra_instructions}" if extra_instructions else ""
    evidence_block = (
        f"\n\nEXTRACTED EVIDENCE (deterministic):\n{evidence_json}"
        if evidence_json
        else ""
    )
    return f"""Synthesize final interview feedback JSON with exactly this structure:

{INTERVIEW_FINAL_JSON_SCHEMA}

SYNTHESIS RULES:
- Treat SPECIALIST REVIEWS (1-5 scores) as primary evidence for rating, strengths, and concerns.
- Use TRANSCRIPT EXCERPT only to verify quotes, fill qa_pairs, and resolve conflicts.
- Balance strengths and concerns — do not overweight EXTRACTED EVIDENCE concerns if specialist scores are mostly 3-5.
- If specialist scores conflict, use Hold; do not default to Reject.
- Every strength/concern must trace to specialist evidence_quotes or EXTRACTED EVIDENCE.
- Do not introduce claims absent from reviews or excerpt.

{INTERVIEW_SYNTHESIS_RATING_GUIDE}

{INTERVIEW_ANALYSIS_STEPS}
{extra}
SPECIALIST REVIEWS:
{reviews_json}
{evidence_block}

TRANSCRIPT EXCERPT (verification):
{transcript_excerpt}
"""


FAIRNESS_CHECK_SYSTEM = f"""You check hiring feedback for unsupported claims or protected-class inferences.

{INTERVIEW_EVIDENCE_RULES}

Return valid JSON only."""


def fairness_check_prompt(feedback_json: str) -> str:
    return f"""Review this hiring feedback for unsupported claims or protected-class inferences.

Return JSON:
{{
  "flags": ["list unsupported or risky claims, empty if none"],
  "adjusted_rating": "Proceed|Hold|Reject — MUST match input rating when flags is empty",
  "notes": ""
}}

RULES:
- If flags is empty, set adjusted_rating to the SAME value as the input rating field.
- Only change adjusted_rating when flags is non-empty and a correction is required.
- Do not downgrade Proceed to Reject unless flags cite serious unsupported claims or bias.

FEEDBACK:
{feedback_json}
"""
