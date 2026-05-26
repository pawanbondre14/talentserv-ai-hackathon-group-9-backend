# MeetPilot AI — Backend

FastAPI service for **meeting minutes** and **interview hiring feedback**: session storage, transcript ingestion, **LangGraph multi-agent pipelines**, Microsoft Teams/OneDrive import, and post-session chat.

**Parent project:** [../README.md](../README.md) · **Multi-agent design:** [../MULTI_AGENT_PLAN.md](../MULTI_AGENT_PLAN.md)

---

## 1. What this backend does

| Area | Description |
|------|-------------|
| **Sessions** | Create, list, search, delete transcript sessions per user |
| **Processing** | `POST /api/sessions/{id}/process` — meeting or interview structured JSON |
| **LangGraph** | Optional orchestrated pipeline: preprocess → route → single or multi-agent subgraph |
| **Interview** | Scorecards, blind mode (PII redaction), panel merge preview |
| **Microsoft** | OAuth + list/import `.vtt` from OneDrive Recordings |
| **Chat** | Context-aware Q&A on transcript + AI output |

---

## 2. Tech stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Uvicorn |
| Auth | Clerk JWT (`CLERK_ISSUER`, `CLERK_JWKS_URL`) |
| Database | Supabase PostgreSQL (SQLAlchemy) |
| LLM | OpenAI (`gpt-4o`, `gpt-4o-mini`) — `LLM_MOCK` for offline demo |
| Orchestration | **LangGraph** (`StateGraph`, `Send` map-reduce) |
| Validation | Pydantic schemas |

---

## 3. Project structure

```
app/
├── main.py                 # FastAPI app, CORS, routers
├── config.py               # Settings (LangGraph, chunking, Microsoft)
├── auth.py                 # Clerk JWT validation
├── database.py
├── models/                 # SQLAlchemy models
├── routes/
│   ├── sessions.py         # Session CRUD, search
│   ├── ingest.py           # Transcript ingest
│   ├── process.py          # Process, output patch, full session
│   ├── interview.py        # Scorecards, panel merge
│   ├── chat.py             # Session chat
│   ├── microsoft.py        # OAuth callback
│   └── teams.py            # Transcript list / import
├── services/
│   ├── graph_runner.py     # LangGraph invoke vs legacy
│   ├── llm.py              # OpenAI complete_json
│   ├── interview_processor.py
│   ├── chunking.py, normalize.py
│   └── ...
├── graphs/
│   ├── parent.py           # preprocess → route → subgraph → validate
│   ├── state.py            # TranscriptState
│   ├── meeting/            # Map-reduce meeting minutes
│   └── interview/          # Classify → reviewers → synthesize → fairness
└── prompts/                # System prompts per node
samples/                    # Test transcripts (see samples/README.md)
tests/                      # Pytest including graph phase A/B/C
supabase/migrations/        # DB schema
```

---

## 4. LangGraph pipeline (multi-agent)

### 4.1 Parent graph

```
START → preprocess → budget_check → route_strategy
          ├─ single_shot      (one LLM call — legacy-equivalent)
          ├─ meeting_graph    (Phase B map-reduce)
          └─ interview_graph  (Phase C specialists)
        → validate_output → END
```

### 4.2 Routing rules (`app/graphs/nodes/route.py`)

| Condition | Path |
|-----------|------|
| `strategy=single` | `single_shot` |
| `strategy=multi` | Mode-specific subgraph |
| `strategy=auto` + words ≥ `MULTI_WORD_THRESHOLD` (default 800) + multiple chunks | Subgraph |
| Interview + `panel_transcripts` | `single_shot` (panel merge handled separately) |

### 4.3 Meeting subgraph

`begin_meeting` → **parallel** `summarize_chunk` (per chunk) → `link_entities` → `merge_actions` → `synthesize_minutes`

### 4.4 Interview subgraph

`begin_interview` → **parallel** `classify_chunk` → `aggregate_classifications` → **parallel** `review_technical` / `review_communication` / `review_culture` → `extract_evidence` → `synthesize_hiring` → `fairness_check`

### 4.5 Model tiers

- **Fast** (`OPENAI_MODEL_FAST`): chunk classify, chunk summarize, dimension reviews, fairness  
- **Strong** (`OPENAI_MODEL`): final synthesis (minutes, hiring decision)

---

## 5. Key API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |
| POST | `/api/sessions` | Create session |
| GET | `/api/sessions` | List sessions |
| GET | `/api/sessions/search` | Full-text search |
| POST | `/api/sessions/{id}/process` | Run AI (`mode`, `strategy`, interview options) |
| GET | `/api/sessions/{id}/full` | Session + output + interview meta |
| PATCH | `/api/sessions/{id}/output` | Save edited JSON |
| GET/POST/DELETE | `/api/sessions/{id}/chat` | Session chat |
| GET | `/api/interview/scorecards` | List scorecard templates |
| POST | `/api/interview/panel-merge` | Preview panel merge |
| GET | `/api/microsoft/auth-url` | Start Microsoft OAuth (requires Clerk token) |
| GET | `/api/teams/transcripts` | List importable VTT files |
| POST | `/api/teams/import` | Import transcript into session |

Interactive docs: **http://localhost:8000/docs**

### Process request body (example)

```json
{
  "mode": "interview",
  "strategy": "auto",
  "interview_options": {
    "scorecard_id": "backend_senior",
    "blind_mode": false
  }
}
```

---

## 6. Environment variables

Copy `.env.example` → `.env`.

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Supabase Postgres URI |
| `CLERK_ISSUER`, `CLERK_JWKS_URL` | Prod | Must match frontend Clerk app |
| `SKIP_AUTH`, `DEV_USER_ID` | Local only | Dev without Clerk |
| `OPENAI_API_KEY` | Yes* | *Or `LLM_MOCK=true` |
| `LANGGRAPH_ENABLED` | No | `true` to use graph pipeline |
| `MULTI_WORD_THRESHOLD` | No | Auto multi-agent threshold (default 800) |
| `LLM_MOCK` | No | Deterministic demo responses |
| `AZURE_*` | Phase 4 | Microsoft Graph (optional) |

---

## 7. Setup & run

```bash
cd talentserv-ai-hackathon-group-9-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

1. Create [Supabase](https://supabase.com) project → run `supabase/migrations/001_initial_schema.sql`.  
2. Create [Clerk](https://clerk.com) app → set issuer + JWKS in `.env`.  
3. Set `OPENAI_API_KEY` or `LLM_MOCK=true`.  
4. For multi-agent demo: `LANGGRAPH_ENABLED=true`.

```bash
uvicorn app.main:app --reload --port 8000
```

---

## 8. Testing

```bash
pytest
```

Graph tests: `tests/test_graph_phase_a.py`, `test_graph_phase_b.py`, `test_graph_phase_c.py`  
Session tests require reachable `DATABASE_URL`.

### Sample transcripts

See [samples/README.md](./samples/README.md):

- Short: `meeting_sample.txt`, `interview_sample.txt`  
- Multi-agent: `meeting_multi_agent_sample.txt`, `interview_multi_agent_sample.txt` + `strategy=multi`

---

## 9. Backend implementation plan (completed phases)

| Step | Module | Status |
|------|--------|--------|
| 1 | FastAPI + Supabase schema + Clerk auth | Done |
| 2 | `llm.py` + meeting/interview prompts + `/process` | Done |
| 3 | `graph_runner` + parent graph (preprocess, validate) | Done |
| 4 | `meeting_graph` map-reduce | Done |
| 5 | `interview_graph` parallel reviewers + fairness | Done |
| 6 | Search index, ingest uploads | Done |
| 7 | Microsoft OAuth + Teams import | Done |
| 8 | Session chat routes | Done |

---

## 10. Deploy notes (Vercel / Render)

- Use Supabase **pooler** URL on serverless (`*.pooler.supabase.com:6543`), not direct `db.*` host.  
- Set `CORS_ORIGINS` and `FRONTEND_URL` to your UI URL.  
- `DEBUG=false`, do not use `BOOTSTRAP_SCHEMA=true` in production.  
- Encode `@` in DB password as `%40`.

---

## 11. Microsoft Connect troubleshooting

`/api/microsoft/auth-url` returns JSON and requires a **Clerk session token** (from the React app), not a bare browser visit.

1. Sign in at http://localhost:5173  
2. **New session** → **Teams / OneDrive** → **Connect Microsoft account**  
3. Without Azure: use **Demo — sample meetings**

Ensure backend `CLERK_ISSUER` matches frontend `VITE_CLERK_PUBLISHABLE_KEY` (same Clerk application).

---

## 12. Related docs

- [Project README](../README.md) — solution plan, demo script, team template  
- [MULTI_AGENT_PLAN.md](../MULTI_AGENT_PLAN.md) — detailed graph specification  
- [PROJECT_PLAN.md](../PROJECT_PLAN.md) — original phase roadmap  
