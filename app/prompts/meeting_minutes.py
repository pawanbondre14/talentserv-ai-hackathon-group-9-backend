MEETING_MINUTES_SYSTEM = """You are an expert meeting scribe. Extract structured meeting minutes from transcripts only.
Return valid JSON only — no markdown fences, no commentary.
Use evidence from the transcript only. For owners not mentioned, use "Unknown".
Use empty arrays [] when nothing applies. Use "None identified" as a single string in arrays only when the rubric expects a placeholder message in follow_ups/risks if truly nothing was said."""


def meeting_minutes_prompt(transcript: str) -> str:
    return f"""Analyze this meeting transcript and return JSON with exactly these keys:

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

TRANSCRIPT:
{transcript}
"""
