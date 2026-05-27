CLASSIFY_CHUNK_SYSTEM = """You classify interview transcript segments for downstream specialist reviewers.
Return valid JSON only."""


def classify_chunk_prompt(chunk_id: str, chunk_text: str) -> str:
    return f"""Classify this interview transcript segment (chunk {chunk_id}).

Return JSON:
{{
  "chunk_id": "{chunk_id}",
  "segment_types": ["technical", "behavioral", "culture"],
  "has_technical_content": true,
  "has_communication_signals": true,
  "has_culture_fit_signals": true,
  "summary": "one sentence"
}}

SEGMENT:
{chunk_text}
"""


REVIEW_TECHNICAL_SYSTEM = """You evaluate technical skills and problem-solving from interview evidence only.
Return valid JSON only."""


def review_technical_prompt(transcript_excerpt: str, classifications: str) -> str:
    return f"""Review technical depth. Return JSON:
{{
  "dimension": "technical",
  "technical_skills": ["skill1"],
  "problem_solving": "assessment",
  "gaps": ["gap1"],
  "score": 1,
  "evidence_quotes": ["exact quote from transcript"],
  "summary": "brief"
}}

CLASSIFICATIONS:
{classifications}

TRANSCRIPT EXCERPT:
{transcript_excerpt}
"""


REVIEW_COMMUNICATION_SYSTEM = """You evaluate communication quality from interview evidence only.
Return valid JSON only."""


def review_communication_prompt(transcript_excerpt: str, classifications: str) -> str:
    return f"""Review communication. Return JSON:
{{
  "dimension": "communication",
  "clarity": "assessment",
  "structure": "assessment",
  "red_flags": [],
  "score": 1,
  "evidence_quotes": ["exact quote"],
  "summary": "brief"
}}

CLASSIFICATIONS:
{classifications}

TRANSCRIPT EXCERPT:
{transcript_excerpt}
"""


REVIEW_CULTURE_SYSTEM = """You evaluate culture fit and motivation signals from interview evidence only.
Return valid JSON only."""


def review_culture_prompt(transcript_excerpt: str, classifications: str) -> str:
    return f"""Review culture fit. Return JSON:
{{
  "dimension": "culture",
  "enthusiasm": "assessment",
  "collaboration_signals": ["signal"],
  "concerns": [],
  "score": 1,
  "evidence_quotes": ["exact quote"],
  "summary": "brief"
}}

CLASSIFICATIONS:
{classifications}

TRANSCRIPT EXCERPT:
{transcript_excerpt}
"""


SYNTHESIZE_HIRING_SYSTEM = """You synthesize specialist interview reviews into hiring feedback for recruiters.
Return valid JSON only. rating must be exactly one of: Proceed, Hold, Reject.
For skill areas not covered, use "Not assessed"."""


def synthesize_hiring_prompt(reviews_json: str, transcript_excerpt: str, extra_instructions: str = "") -> str:
    extra = f"\n\n{extra_instructions}" if extra_instructions else ""
    return f"""Synthesize final interview feedback JSON with exactly these keys:

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
  "qa_pairs": [{{"question": "", "answer": "", "notes": ""}}],
  "scorecard_scores": []
}}

Use specialist reviews as primary evidence. Include qa_pairs when clear in transcript.
{extra}
SPECIALIST REVIEWS:
{reviews_json}

TRANSCRIPT EXCERPT:
{transcript_excerpt}
"""


FAIRNESS_CHECK_SYSTEM = """You check hiring feedback for unsupported claims or protected-class inferences.
Return valid JSON only."""


def fairness_check_prompt(feedback_json: str) -> str:
    return f"""Review this hiring feedback. Return JSON:
{{
  "flags": ["list unsupported or risky claims, empty if none"],
  "adjusted_rating": "Proceed|Hold|Reject or same as input",
  "notes": ""
}}

FEEDBACK:
{feedback_json}
"""
