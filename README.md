# MeetingFeed AI — Backend

FastAPI backend for **Meeting Feed Generator AI**: sessions, transcripts, AI processing (later phases), and Supabase Postgres.

## Phase 1

- Health checks, Clerk JWT, session CRUD + search, Supabase schema

## Phase 4 (current)

- Microsoft OAuth + OneDrive `Recordings` folder listing (`.vtt` transcripts)
- Mock Teams meetings (always available)
- `GET /api/teams/transcripts`, `POST /api/teams/import`
- `GET /api/microsoft/auth-url`, callback, disconnect

## Phase 2

- `POST /api/sessions/{id}/process` — meeting minutes or interview feedback
- `GET /api/sessions/{id}/full` — session + output
- `PATCH /api/sessions/{id}/output` — save edited JSON
- Providers: `anthropic` (default) or `openai`; set `LLM_MOCK=true` without keys

## Setup

```bash
cd talentserv-ai-hackathon-group-9-backend
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

1. Create a [Supabase](https://supabase.com) project.
2. Run `supabase/migrations/001_initial_schema.sql` in **SQL Editor**.
3. Copy **Database → Connection string (URI)** into `DATABASE_URL`.
4. Create a [Clerk](https://clerk.com) app; set `CLERK_ISSUER` and `CLERK_JWKS_URL` (Issuer URL + `/.well-known/jwks.json`).

Local dev without Clerk:

```env
SKIP_AUTH=true
DEV_USER_ID=dev_user_local
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

## Tests

```bash
pytest
```

Session tests require a reachable `DATABASE_URL`.
