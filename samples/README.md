# Sample transcripts for MeetPilot / HackFeed

## Phase A (current) — single-shot only

| File | Mode | Words | Use |
|------|------|-------|-----|
| `meeting_sample.txt` | Meeting | ~80 | Quick smoke test |
| `interview_sample.txt` | Interview | ~120 | Quick smoke test |
| `meeting_long_sample.txt` | Meeting | ~850 | Realistic short meeting |
| `interview_long_sample.txt` | Interview | ~1,080 | Realistic short interview |

These work with `LANGGRAPH_ENABLED=true` but still run **single_shot** (one LLM call).

## Multi-agent ready

| File | Mode | Words | Trigger |
|------|------|-------|---------|
| `meeting_multi_agent_sample.txt` | Meeting | ~4,855 | `strategy=multi` or `auto` when words ≥ 800 |
| `interview_multi_agent_sample.txt` | Interview | ~4,918 | `strategy=multi` or `auto` when words ≥ 800 |

**Meeting (Phase B):** chunk → parallel summarize → merge → synthesize.

**Interview (Phase C):** classify chunks → parallel technical / communication / culture reviewers → evidence → synthesize hiring → fairness check.

```json
POST /api/sessions/{id}/process
{ "strategy": "multi" }
```

Requires `LANGGRAPH_ENABLED=true`. Interview panels (`panel_transcripts`) still use **single_shot** merge.

## Standalone multi-agent (works today)

The separate prototype in `python/python/interview_agent/` has its own samples:

- `transcripts/senior_backend_engineer.txt`
- `transcripts/full_stack_developer.txt`
- `transcripts/frontend_developer.txt`
- etc.

Run: `python -m interview_agent.main senior_backend_engineer`

That uses Supervisor → Skill / Communication / Sentiment → Decision (true multi-agent).
