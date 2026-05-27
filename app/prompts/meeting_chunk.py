CHUNK_SUMMARY_SYSTEM = """You extract partial meeting notes from one transcript segment.
Return valid JSON only — no markdown fences.
Use evidence from the segment only. For unknown owners use "Unknown"."""


def chunk_summary_prompt(chunk_id: str, chunk_text: str) -> str:
    return f"""Analyze this meeting transcript SEGMENT (chunk {chunk_id}) and return JSON:

{{
  "chunk_id": "{chunk_id}",
  "discussion_points": [
    {{"topic": "", "summary": "", "participants": []}}
  ],
  "decisions": [
    {{"decision": "", "rationale": "", "owner": ""}}
  ],
  "action_items": [
    {{"task": "", "owner": "", "due_date": "not specified", "priority": "Medium"}}
  ],
  "risks": [],
  "follow_ups": []
}}

SEGMENT:
{chunk_text}
"""


MERGE_ACTIONS_SYSTEM = """You deduplicate and merge meeting decisions and action items from chunk summaries.
Return valid JSON only. Combine near-duplicates; keep distinct items separate."""


def merge_actions_prompt(merged_outline: str) -> str:
    return f"""From these chunk-level meeting extractions, return JSON:

{{
  "decisions": [{{"decision": "", "rationale": "", "owner": ""}}],
  "action_items": [{{"task": "", "owner": "", "due_date": "not specified", "priority": "High|Medium|Low"}}],
  "risks": [],
  "follow_ups": []
}}

CHUNK DATA:
{merged_outline}
"""


SYNTHESIZE_MINUTES_SYSTEM = """You produce final structured meeting minutes from merged facts.
Return valid JSON matching the required schema exactly. No markdown fences."""


def synthesize_minutes_prompt(merged_facts: str, full_transcript_excerpt: str) -> str:
    return f"""Create final meeting minutes JSON with exactly these keys:

{{
  "executive_summary": "2-3 sentences",
  "discussion_points": [
    {{"topic": "", "summary": "", "participants": []}}
  ],
  "decisions": [
    {{"decision": "", "rationale": "", "owner": ""}}
  ],
  "action_items": [
    {{"task": "", "owner": "", "due_date": "YYYY-MM-DD or not specified", "priority": "High|Medium|Low"}}
  ],
  "risks": [],
  "follow_ups": []
}}

Use MERGED FACTS as primary source; verify tone against transcript excerpt if needed.

MERGED FACTS:
{merged_facts}

TRANSCRIPT EXCERPT (first ~3000 chars):
{full_transcript_excerpt}
"""
