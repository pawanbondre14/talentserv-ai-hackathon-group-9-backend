# MeetPilot AI — Backend

FastAPI service for **meeting minutes** and **interview hiring feedback**: session storage, transcript ingestion, **LangGraph multi-agent pipelines**, Microsoft Teams/OneDrive import, and post-session chat.

**Related docs:** [Frontend README](../talentserv-ai-hackathon-group-9-ui/README.md) · [Project README](../talentserv-ai-hackathon-group-9-ui/Project_README.md) · [Teams / OneDrive setup](./TEAMS_ONEDRIVE_SETUP.md) · [Multi-agent design](../talentserv-ai-hackathon-group-9-ui/MULTI_AGENT_PLAN.md)

---

## 1. What this backend does

| Area | Description |
|------|-------------|
| **Sessions** | Create, list, search, delete transcript sessions per user |
| **Processing** | `POST /api/sessions/{id}/process` — meeting or interview structured JSON |
| **LangGraph** | Optional orchestrated pipeline: preprocess → route → single or multi-agent subgraph |
| **Interview** | Scorecards, blind mode (PII redaction), panel merge preview |
| **Microsoft** | OAuth + browse/import `.txt` and `.vtt` from OneDrive Recordings |
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
│   ├── onedrive.py         # Folder browser + import
│   └── teams.py            # Legacy transcript list / import aliases
├── services/
│   ├── graph_runner.py     # LangGraph invoke vs legacy
│   ├── llm.py              # OpenAI complete_json
│   ├── interview_processor.py
│   ├── teams_service.py    # OneDrive / Teams Graph
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
| GET | `/api/health/db` | Database connectivity |
| POST | `/api/sessions` | Create session |
| GET | `/api/sessions` | List sessions |
| GET | `/api/sessions/search` | Full-text search |
| POST | `/api/sessions/{id}/process` | Run AI (`mode`, `strategy`, interview options) |
| GET | `/api/sessions/{id}/full` | Session + output + interview meta |
| PATCH | `/api/sessions/{id}/output` | Save edited JSON |
| GET/POST/DELETE | `/api/sessions/{id}/chat` | Session chat |
| GET | `/api/interview/scorecards` | List scorecard templates |
| POST | `/api/interview/panel-merge` | Preview panel merge |
| GET | `/api/microsoft/status` | Connection + Azure config flags |
| GET | `/api/microsoft/auth-url` | Start Microsoft OAuth (requires Clerk token) |
| GET | `/api/microsoft/callback` | OAuth redirect handler |
| POST | `/api/microsoft/disconnect` | Clear Microsoft refresh token |
| GET | `/api/onedrive/browse?folder_id=root` | Browse folders + transcript files |
| GET | `/api/onedrive/recordings` | Recordings folder shortcut |
| POST | `/api/onedrive/import` | Import selected file → session |
| GET | `/api/teams/transcripts` | Legacy alias (recordings list) |
| POST | `/api/teams/import` | Legacy alias (import) |

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
| `DATABASE_URL` | Yes | Supabase Postgres URI (pooler port **6543** on serverless) |
| `CLERK_ISSUER`, `CLERK_JWKS_URL` | Prod | Must match frontend Clerk app |
| `SKIP_AUTH`, `DEV_USER_ID` | Local only | Dev without Clerk |
| `OPENAI_API_KEY` | Yes* | *Or `LLM_MOCK=true` |
| `LANGGRAPH_ENABLED` | No | `true` to use graph pipeline |
| `MULTI_WORD_THRESHOLD` | No | Auto multi-agent threshold (default 800) |
| `LLM_MOCK` | No | Deterministic demo responses |
| `AZURE_*`, `MS_TOKEN_ENCRYPTION_KEY` | Phase 4 | Microsoft Graph / OneDrive (optional) |

**Full Azure setup:** [TEAMS_ONEDRIVE_SETUP.md](./TEAMS_ONEDRIVE_SETUP.md)

---

## 7. Setup & run

```bash
cd talentserv-ai-hackathon-group-9-backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
```

1. Create a [Supabase](https://supabase.com) project and run `supabase/migrations/001_initial_schema.sql` in the SQL Editor.
2. Set `DATABASE_URL` (use the **Transaction pooler**, port **6543**, for serverless).
3. Create a [Clerk](https://clerk.com) app; set `CLERK_ISSUER` and `CLERK_JWKS_URL`.
4. Set `OPENAI_API_KEY` or `LLM_MOCK=true`. For multi-agent demo: `LANGGRAPH_ENABLED=true`.
5. Optional: Azure vars for live OneDrive — see [TEAMS_ONEDRIVE_SETUP.md](./TEAMS_ONEDRIVE_SETUP.md).

Local dev without Clerk:

```env
SKIP_AUTH=true
DEV_USER_ID=dev_user_local
```

```bash
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/api/health

---

## 8. Testing

```bash
pytest
```

Graph tests: `tests/test_graph_phase_a.py`, `test_graph_phase_b.py`, `test_graph_phase_c.py`  
Session and OneDrive tests require a reachable `DATABASE_URL`. Mock Teams/OneDrive tests run without Azure.

### Sample transcripts

See [samples/README.md](./samples/README.md):

- Short: `meeting_sample.txt`, `interview_sample.txt`  
- Multi-agent: `meeting_multi_agent_sample.txt`, `interview_multi_agent_sample.txt` + `strategy=multi`
---

## 9. Implementation phases

| Phase | Focus | Status |
|-------|--------|--------|
| **1** | Health, Clerk JWT, session CRUD + search, Supabase schema | Done |
| **2** | LLM processing, structured JSON output, meeting + interview modes | Done |
| **2.5** | LangGraph orchestration (single-shot vs multi-agent routing) | Done |
| **3** | File upload (`.txt`), search, ingest normalization | Done |
| **4** | Microsoft OAuth + OneDrive folder browser + import (`.txt`, `.vtt`) | Done |
| **5** | Interview scorecards, blind mode, panel merge API | Done |
| **6** | Post-session AI chat on processed sessions | Done |

---

## 10. Deploy (Vercel / serverless)

**Do not** use the direct `db.xxx.supabase.co` URL on Vercel — Lambda often cannot connect over **IPv6**.

1. Supabase → **Database** → **Connect** → **Transaction pooler** (port **6543**).
2. Host must look like `aws-0-xx.pooler.supabase.com` (not `db....supabase.co`).
3. Encode `@` in password as `%40` in `DATABASE_URL`.
4. Set `DEBUG=false`; do **not** set `BOOTSTRAP_SCHEMA=true` on Vercel.
5. Set `CORS_ORIGINS` and `FRONTEND_URL` to your frontend URL.
6. Add production `AZURE_REDIRECT_URI` in Entra and backend env.

Example:

```env
DATABASE_URL=postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres?sslmode=require
DEBUG=false
ENVIRONMENT=production
CORS_ORIGINS=https://your-app.vercel.app
FRONTEND_URL=https://your-app.vercel.app
```

Redeploy after changing env vars.

---

## 11. Microsoft Connect troubleshooting

`/api/microsoft/auth-url` is **not** a page you open in the browser. It requires a **Clerk login token**.

1. Open the React app at http://localhost:5173 and **sign in**.
2. Go to **New session** → **Teams / OneDrive** tab.
3. Click **Connect Microsoft account**.

If you see `401 Invalid or expired token`:

- Backend `.env`: `CLERK_ISSUER` and `CLERK_JWKS_URL` must match the same Clerk app as frontend `VITE_CLERK_PUBLISHABLE_KEY`.
- Sign out and sign in again.

**Without Azure** you can still use **Demo — sample folders** (no Microsoft sign-in required).

Minimal backend env for live OneDrive:

```env
TEAMS_INTEGRATION_MODE=auto
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=consumers
AZURE_SCOPES=openid profile offline_access User.Read Files.Read
AZURE_REDIRECT_URI=http://localhost:8000/api/microsoft/callback
FRONTEND_URL=http://localhost:5173
MS_TOKEN_ENCRYPTION_KEY=your-fernet-key
```

After changing scopes, users must **disconnect and reconnect** Microsoft in the UI.

---

## 12. Related docs

- [Frontend README](../talentserv-ai-hackathon-group-9-ui/README.md) — UI setup and usage  
- [Project README](../talentserv-ai-hackathon-group-9-ui/Project_README.md) — solution plan, demo script  
- [MULTI_AGENT_PLAN.md](../talentserv-ai-hackathon-group-9-ui/MULTI_AGENT_PLAN.md) — detailed graph specification  
- [TEAMS_ONEDRIVE_SETUP.md](./TEAMS_ONEDRIVE_SETUP.md) — Azure app registration and OAuth
