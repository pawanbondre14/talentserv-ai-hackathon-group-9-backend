from app.prompts._shared import (
    MEETING_ANALYSIS_STEPS,
    MEETING_CHUNK_JSON_SCHEMA,
    MEETING_EVIDENCE_RULES,
    MEETING_FINAL_JSON_SCHEMA,
)

CHUNK_SUMMARY_SYSTEM = f"""You extract partial meeting notes from one transcript segment.

{MEETING_EVIDENCE_RULES}

Return valid JSON only."""


def chunk_summary_prompt(chunk_id: str, chunk_text: str) -> str:
    return f"""Analyze this meeting transcript SEGMENT (chunk {chunk_id}).

Return JSON matching this structure (set chunk_id to "{chunk_id}"):

{MEETING_CHUNK_JSON_SCHEMA}

{MEETING_ANALYSIS_STEPS}

SEGMENT:
{chunk_text}
"""


MERGE_ACTIONS_SYSTEM = f"""You deduplicate and merge meeting decisions and action items from chunk summaries.

{MEETING_EVIDENCE_RULES}

Combine near-duplicates; keep distinct items separate.
Preserve source_quote and chunk_id when merging; combine chunk_ids for merged items.
Return valid JSON only."""


def merge_actions_prompt(merged_outline: str) -> str:
    return f"""From these chunk-level meeting extractions, return JSON:

{{
  "decisions": [{{"decision": "", "rationale": "", "owner": "", "source_quote": "", "chunk_id": ""}}],
  "action_items": [{{"task": "", "owner": "", "due_date": "not specified", "priority": "High|Medium|Low", "source_quote": "", "chunk_id": ""}}],
  "risks": [],
  "follow_ups": []
}}

CHUNK DATA:
{merged_outline}
"""


SYNTHESIZE_MINUTES_SYSTEM = f"""You produce final structured meeting minutes from merged facts.

{MEETING_EVIDENCE_RULES}

Return valid JSON matching the required schema exactly. No markdown fences."""


def synthesize_minutes_prompt(merged_facts: str, full_transcript_excerpt: str) -> str:
    return f"""Create final meeting minutes JSON with exactly this structure:

{MEETING_FINAL_JSON_SCHEMA}

SYNTHESIS RULES:
- Use MERGED FACTS as the primary source for decisions, action_items, risks, and follow_ups.
- Use TRANSCRIPT EXCERPT only to verify tone, fill discussion_points gaps, and resolve conflicts.
- Do not add decisions or action items absent from MERGED FACTS unless clearly supported in the excerpt.
- If chunk summaries conflict, note the conflict briefly in the relevant item rationale.

{MEETING_ANALYSIS_STEPS}

MERGED FACTS:
{merged_facts}

TRANSCRIPT EXCERPT (verification):
{full_transcript_excerpt}
"""
