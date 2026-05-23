# MeetPilot AI — Backend

FastAPI backend for **Turn talk into action with AI AI**: sessions, transcripts, AI processing (later phases), and Supabase Postgres.

## Phase 1

- Health checks, Clerk JWT, session CRUD + search, Supabase schema

## Microsoft Connect troubleshooting

`/api/microsoft/auth-url` is **not** a page you open in the browser. It is a JSON API that requires your **Clerk login token**.

1. Open the **React app** at http://localhost:5173 and **sign in**.
2. Go to **New session** → **Teams / OneDrive** tab.
3. Click **Connect Microsoft account** (you will be redirected to Microsoft).

If you see `401 Invalid or expired token` in Swagger or the browser URL bar, you are not sending a valid Clerk session. Fix:

- Backend `.env`: `CLERK_ISSUER` and `CLERK_JWKS_URL` must match [Clerk Dashboard](https://dashboard.clerk.com) → your app → **API keys** (Issuer URL + `/.well-known/jwks.json`).
- Frontend `.env`: `VITE_CLERK_PUBLISHABLE_KEY` from the **same** Clerk application.
- Sign out and sign in again in the app.

**Without Azure** you can still use **Demo — sample meetings** (no Microsoft sign-in required).

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

## Deploy backend (Vercel / serverless)

**Do not** use the direct `db.xxx.supabase.co` URL on Vercel — Lambda often cannot connect over **IPv6** (`Cannot assign requested address`).

1. Supabase → **Project Settings** → **Database** → **Connect**.
2. Choose **ORMs** / **URI**.
3. Mode: **Transaction** (port **6543**).
4. Copy the host that looks like `aws-0-xx-xx-xx.pooler.supabase.com` (not `db....supabase.co`).
5. Set `DATABASE_URL` in Vercel env (encode `@` in password as `%40`).
6. Set `DEBUG=false` and do **not** set `BOOTSTRAP_SCHEMA=true` on Vercel.
7. Run `supabase/migrations/001_initial_schema.sql` once in Supabase SQL Editor (tables already exist).

Example:

```env
DATABASE_URL=postgresql://postgres.malzkqtfczuoarpnhxrm:YOUR_ENCODED_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require
DEBUG=false
ENVIRONMENT=production
CORS_ORIGINS=https://your-app.vercel.app
FRONTEND_URL=https://your-app.vercel.app
```

Redeploy after changing env vars.

## Tests

```bash
pytest
```

Session tests require a reachable `DATABASE_URL`.
