# Teams / OneDrive Transcript Integration — Setup Guide

This guide explains how to configure MeetPilot AI to import **`.txt`** and **`.vtt`** transcript files from a user's **personal Microsoft OneDrive** account.

**Related docs:** [Backend README](./README.md) (Phase 4) · [Project README](../talentserv-ai-hackathon-group-9-ui/Project_README.md)

---

## Overview

| Capability | Description |
|------------|-------------|
| **OAuth** | Backend Microsoft OAuth (Clerk login required first) |
| **Browse** | Folder browser for OneDrive (folders + `.txt` / `.vtt` files) |
| **Import** | Download file via Graph API → parse VTT → create session |
| **Demo mode** | Sample folders work without Azure (mock data in `samples/teams/`) |

**Supported account type:** Personal Microsoft accounts (`@outlook.com`, `@hotmail.com`, `@live.com`).

**Not included:** Microsoft OneDrive File Picker v8 (frontend MSAL). All Graph calls run on the backend.

---

## Architecture

```
React UI (Clerk auth)
    → GET /api/microsoft/auth-url
    → Microsoft login (consumers tenant)
    → GET /api/microsoft/callback → stores encrypted refresh token in Postgres

User browses OneDrive
    → GET /api/onedrive/browse?folder_id=root
    → Backend calls Microsoft Graph with refresh token

User imports file
    → POST /api/onedrive/import
    → Graph download → VTT/TXT parse → session created
    → Optional: POST /api/sessions/{id}/process (AI)
```

---

## Prerequisites

- Backend running (`uvicorn app.main:app --reload --port 8000`)
- Frontend running (`npm run dev` → http://localhost:5173)
- [Clerk](https://clerk.com) configured (user must sign in before connecting Microsoft)
- [Supabase Postgres](https://supabase.com) with schema applied (`supabase/migrations/001_initial_schema.sql`)

---

## Step 1 — Register Azure app (Microsoft Entra)

1. Open [Microsoft Entra admin center](https://entra.microsoft.com) → **App registrations** → **New registration**.

2. Configure:
   | Field | Value |
   |-------|-------|
   | **Name** | e.g. `MeetPilot OneDrive` |
   | **Supported account types** | **Personal Microsoft accounts only** |
   | **Redirect URI** | Platform: **Web** → `http://localhost:8000/api/microsoft/callback` |

3. After creation, copy from **Overview**:
   - **Application (client) ID** → `AZURE_CLIENT_ID`

4. **Authentication** → confirm Web redirect URI:
   ```
   http://localhost:8000/api/microsoft/callback
   ```
   Must match `AZURE_REDIRECT_URI` exactly (no trailing slash).

5. **Certificates & secrets** → **New client secret** → copy the **Value** → `AZURE_CLIENT_SECRET`.

6. **API permissions** → **Microsoft Graph** → **Delegated**:
   - `User.Read`
   - `Files.Read`

   Admin consent is usually not required for personal accounts.

---

## Step 2 — Backend environment variables

Edit `talentserv-ai-hackathon-group-9-backend/.env`:

```env
# Microsoft Graph / OneDrive
TEAMS_INTEGRATION_MODE=auto
AZURE_CLIENT_ID=your-application-client-id
AZURE_CLIENT_SECRET=your-client-secret-value
AZURE_TENANT_ID=consumers
AZURE_SCOPES=openid profile offline_access User.Read Files.Read
AZURE_REDIRECT_URI=http://localhost:8000/api/microsoft/callback
FRONTEND_URL=http://localhost:5173

# Recommended for production (encrypts Microsoft refresh tokens)
MS_TOKEN_ENCRYPTION_KEY=your-fernet-key
```

Generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

| Variable | Notes |
|----------|-------|
| `AZURE_TENANT_ID=consumers` | Best for personal-only apps. `common` also works. |
| `TEAMS_INTEGRATION_MODE=auto` | Uses live OneDrive when Azure is configured and user is connected; otherwise demo mock data. |
| `TEAMS_INTEGRATION_MODE=mock` | Force demo mode always. |
| `TEAMS_INTEGRATION_MODE=live` | Require Microsoft connection (no mock fallback). |

**Restart the backend** after changing `.env`:

```bash
cd talentserv-ai-hackathon-group-9-backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

---

## Step 3 — Frontend environment

Edit `talentserv-ai-hackathon-group-9-ui/.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_CLERK_PUBLISHABLE_KEY=your-clerk-publishable-key
```

No Azure variables are needed in the frontend. Microsoft OAuth is handled entirely by the backend.

---

## Step 4 — Connect and import (user flow)

1. Sign in to MeetPilot at http://localhost:5173
2. Go to **New session** → **Teams / OneDrive** tab
3. Click **Connect Microsoft account**
4. Sign in with a **personal** Microsoft account and accept permissions
5. You are redirected back with `?teams=connected`
6. Browse folders at the OneDrive root
7. Open folders or click **Import** on a `.txt` or `.vtt` file
8. Optionally enable **Generate AI after import** before importing

**UI notes:**
- **Recordings shortcut** appears only before Microsoft is connected (demo / quick access).
- After connect, browse your full OneDrive tree for transcript files.

---

## API endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/microsoft/status` | Connection + Azure config status |
| `GET` | `/api/microsoft/auth-url` | OAuth URL (requires Clerk Bearer token) |
| `GET` | `/api/microsoft/callback` | OAuth callback (Microsoft redirects here) |
| `POST` | `/api/microsoft/disconnect` | Clear stored refresh token |
| `GET` | `/api/onedrive/browse?folder_id=root` | List folders + eligible files |
| `GET` | `/api/onedrive/recordings` | List Recordings folder items |
| `POST` | `/api/onedrive/import` | Import file into a new session |
| `GET` | `/api/teams/transcripts` | Legacy alias for recordings list |
| `POST` | `/api/teams/import` | Legacy alias for import |

### Import request body

```json
{
  "item_id": "onedrive-drive-item-id",
  "source": "onedrive",
  "mode": "meeting",
  "title": "Optional session title",
  "file_name": "standup.vtt"
}
```

---

## Demo mode (no Azure)

If Azure env vars are missing or the user is not connected, the app shows **Demo — sample folders** using:

- `samples/teams/mock_meetings.json`
- `samples/teams/*.vtt`

No Microsoft sign-in required for demo imports.

---

## Production deployment

### Azure app

Add production redirect URI in Entra:

```
https://your-backend-host/api/microsoft/callback
```

### Backend env (example)

```env
AZURE_REDIRECT_URI=https://your-backend-host/api/microsoft/callback
FRONTEND_URL=https://your-frontend-host
CORS_ORIGINS=https://your-frontend-host
AZURE_TENANT_ID=consumers
MS_TOKEN_ENCRYPTION_KEY=<strong-fernet-key>
DEBUG=false
```

Redeploy after env changes. Run DB migration once in Supabase if not already applied.

---

## Troubleshooting

### Empty folder / no files shown

- Only **`.txt`**, **`.vtt`**, and files with `"transcript"` in the name are listed.
- Personal OneDrive may not have a `Recordings` folder — browse other folders instead.

### Import fails / empty transcript

- File may exceed 10 MB limit.
- File encoding must be readable (UTF-8 or latin-1 for `.txt`).

### After changing scopes

Users must **Disconnect** → **Connect** again in the UI.

---

## References

- [Microsoft Graph — driveItem get content](https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0)
- [Microsoft Graph — list children](https://learn.microsoft.com/en-us/graph/api/driveitem-list-children?view=graph-rest-1.0)
- [OneDrive permission scopes](https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/permissions_reference?view=odsp-graph-online)
