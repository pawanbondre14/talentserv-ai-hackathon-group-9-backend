"""Shared prompt fragments for interview and meeting pipelines."""

# ---------------------------------------------------------------------------
# Evidence contracts
# ---------------------------------------------------------------------------

EVIDENCE_RULES_BASE = """EVIDENCE RULES:
- Use only text present in the provided transcript or segment.
- Do not invent participants, decisions, tasks, ratings, or quotes.
- If a topic was not discussed, use "Not assessed" (interview) or omit from lists (meeting).
- Separate facts (verbatim quotes) from interpretation (your judgment).
- Do not infer protected attributes (age, religion, family status, accent, nationality, etc.).
- When evidence is weak or ambiguous, set confidence to low, medium, or high.
- Return valid JSON only — no markdown fences, no commentary."""

INTERVIEW_EVIDENCE_RULES = f"""{EVIDENCE_RULES_BASE}
- Every strength and concern must include at least one supporting quote (≤25 words) in evidence_items or qa_pairs notes.
- rating must be exactly one of: Proceed, Hold, Reject.
- For skill areas not covered in the transcript, use "Not assessed" in skill_observations."""

MEETING_EVIDENCE_RULES = f"""{EVIDENCE_RULES_BASE}
- Every decision and action_item must include a source_quote (≤25 words) from the transcript.
- For owners not mentioned in the transcript, use "Unknown".
- Use empty arrays [] when a category has no items; do not fabricate placeholders except follow_ups/risks may use "None identified" only when truly nothing was said."""

# ---------------------------------------------------------------------------
# Interview: unified final schema + rubrics
# ---------------------------------------------------------------------------

INTERVIEW_FINAL_JSON_SCHEMA = """{
  "candidate_summary": "2-3 sentences grounded in evidence",
  "skill_observations": {
    "technical_skills": "",
    "communication": "",
    "problem_solving": "",
    "culture_fit": ""
  },
  "strengths": ["each strength must be supportable from transcript"],
  "concerns": ["each concern must be supportable from transcript"],
  "communication_assessment": "",
  "rating": "Proceed|Hold|Reject",
  "rationale": "tie to evidence; explain rating",
  "follow_up_questions": [],
  "qa_pairs": [{"question": "", "answer": "", "notes": ""}],
  "evidence_items": [{"quote": "", "competency": "", "signal": "positive|negative|neutral", "chunk_id": ""}],
  "missing_topics": ["competencies not discussed"],
  "confidence": "high|medium|low",
  "scorecard_scores": []
}"""

INTERVIEW_RATING_RUBRIC = """RATING RUBRIC (final hiring decision — not the 1-5 dimension scores):
- Proceed: candidate meets the role bar overall; most core competencies show adequate-to-strong evidence (typical dimension scores 3-5). Coachable gaps are OK. Do NOT reject only because some topics were not discussed — use "Not assessed" instead.
- Hold: mixed signals, inconsistent depth, or important areas need follow-up; not enough evidence to Proceed confidently.
- Reject: sustained weakness across core competencies with transcript evidence (typical dimension scores 1-2), repeated incorrect or vague answers, or clear red flags. Use Reject sparingly — one weak area alone is usually Hold, not Reject."""

INTERVIEW_SYNTHESIS_RATING_GUIDE = """MAP SPECIALIST SCORES (1-5) TO FINAL RATING:
- Average dimension score >= 3.5 with no dimension below 2 → lean Proceed unless red flags.
- Average 2.5-3.4 or mixed scores → lean Hold.
- Average < 2.5 or multiple dimensions at 1-2 → lean Reject.
- missing_topics alone must NOT drive Reject; use "Not assessed" in skill_observations."""

INTERVIEW_ANALYSIS_STEPS = """ANALYSIS STEPS (follow in order):
1. Identify interviewer vs candidate turns where possible.
2. Extract distinct Q&A exchanges into qa_pairs first.
3. Collect verbatim evidence_items for positive AND neutral competency signals (not only negatives).
4. Fill skill_observations; use "Not assessed" when not discussed.
5. List missing_topics only for competencies never covered (do not treat these as automatic concerns).
6. Balance strengths and concerns — include clear positives when the candidate answered well.
7. Assign rating using the rubric and overall performance; set confidence based on evidence density."""

SCORE_SCALE_RUBRIC = """SCORE SCALE (1-5 for dimension/specialist reviews):
1 = no evidence or clearly weak
2 = superficial or incorrect
3 = adequate with gaps
4 = strong with concrete examples
5 = exceptional depth, tradeoffs, and ownership"""

SCORE_FIELD_INSTRUCTION = """SCORE FIELD (critical):
- "score" MUST be an integer from 1 to 5 using the scale above.
- Do NOT default to 1. Use 1 only when the excerpt has no relevant evidence or clear failure.
- If the candidate gives concrete examples (projects, tools, trade-offs), score is usually 3-5.
- JSON examples below use 4 only as a format placeholder — replace with your real assessment."""

INTERVIEW_TRANSCRIPT_FORMAT_NOTE = """TRANSCRIPT FORMAT:
- Some transcripts repeat similar paragraphs (e.g. "On topic N...") — evaluate the skills and examples described, not repetition alone.
- Treat the closing interviewer summary as strong evidence when present (e.g. proceed to next round, strong technical depth)."""

# ---------------------------------------------------------------------------
# Meeting: unified final schema
# ---------------------------------------------------------------------------

MEETING_FINAL_JSON_SCHEMA = """{
  "executive_summary": "2-3 sentences",
  "discussion_points": [
    {"topic": "", "summary": "", "participants": [], "source_quote": ""}
  ],
  "decisions": [
    {"decision": "", "rationale": "", "owner": "", "source_quote": "", "chunk_id": ""}
  ],
  "action_items": [
    {"task": "", "owner": "", "due_date": "YYYY-MM-DD or not specified", "priority": "High|Medium|Low", "source_quote": "", "chunk_id": ""}
  ],
  "risks": [],
  "follow_ups": [],
  "confidence": "high|medium|low"
}"""

MEETING_ANALYSIS_STEPS = """ANALYSIS STEPS (follow in order):
1. Identify topics and who spoke about each.
2. Extract decisions with rationale and owner; attach source_quote per item.
3. Extract action items with owner, due date if stated, priority, and source_quote.
4. Capture risks and follow-ups only if explicitly discussed.
5. Write executive_summary last, summarizing outcomes not process."""

MEETING_CHUNK_JSON_SCHEMA = """{
  "chunk_id": "",
  "topics": ["main topics in this segment"],
  "speakers": ["names or roles mentioned"],
  "discussion_points": [
    {"topic": "", "summary": "", "participants": [], "source_quote": ""}
  ],
  "decisions": [
    {"decision": "", "rationale": "", "owner": "", "source_quote": ""}
  ],
  "action_items": [
    {"task": "", "owner": "", "due_date": "not specified", "priority": "Medium", "source_quote": ""}
  ],
  "risks": [],
  "follow_ups": [],
  "key_quotes": [{"speaker": "", "quote": ""}]
}"""
