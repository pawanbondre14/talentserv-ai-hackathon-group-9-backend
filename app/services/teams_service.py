import json
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import Settings
from app.services.token_crypto import decrypt_token, encrypt_token
from app.services.vtt_parser import vtt_to_plain_text

logger = logging.getLogger(__name__)

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples" / "teams"


@dataclass
class TeamsTranscriptItem:
    id: str
    title: str
    date: str
    source: str  # mock | onedrive
    file_name: str | None = None


class TeamsService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _use_live(self, user) -> bool:
        if self.settings.teams_integration_mode == "mock":
            return False
        if not self.settings.azure_client_id or not self.settings.azure_client_secret:
            return False
        if self.settings.teams_integration_mode == "live":
            return bool(user.ms_refresh_token_enc)
        return bool(user.ms_refresh_token_enc)

    def _list_mock(self) -> list[TeamsTranscriptItem]:
        path = SAMPLES_DIR / "mock_meetings.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [
            TeamsTranscriptItem(
                id=item["id"],
                title=item["title"],
                date=item["date"],
                source="mock",
                file_name=item.get("transcript_file"),
            )
            for item in raw
        ]

    async def list_transcripts(self, user, db) -> tuple[list[TeamsTranscriptItem], str]:
        if self._use_live(user):
            try:
                items = await self._list_onedrive_recordings(user, db)
                return items, "live"
            except Exception as exc:
                logger.warning("OneDrive listing failed, falling back to mock: %s", exc)
        return self._list_mock(), "mock"

    async def _get_access_token(self, user, db) -> str:
        if not user.ms_refresh_token_enc:
            raise ValueError("Microsoft account not connected.")
        refresh = decrypt_token(self.settings, user.ms_refresh_token_enc)
        tenant = self.settings.azure_tenant_id or "common"
        url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        data = {
            "client_id": self.settings.azure_client_id,
            "client_secret": self.settings.azure_client_secret,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
            "scope": self.settings.azure_scopes,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=data)
            resp.raise_for_status()
            payload = resp.json()
        access = payload.get("access_token")
        if not access:
            raise ValueError("No access token from Microsoft.")
        if payload.get("refresh_token"):
            user.ms_refresh_token_enc = encrypt_token(self.settings, payload["refresh_token"])
            db.commit()
        return access

    async def _list_onedrive_recordings(self, user, db) -> list[TeamsTranscriptItem]:
        token = await self._get_access_token(user, db)
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://graph.microsoft.com/v1.0/me/drive/root:/Recordings:/children"
        items: list[TeamsTranscriptItem] = []
        async with httpx.AsyncClient(timeout=30) as client:
            while url:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                for entry in data.get("value", []):
                    name = entry.get("name", "")
                    lower = name.lower()
                    if not (lower.endswith(".vtt") or "transcript" in lower):
                        continue
                    modified = entry.get("lastModifiedDateTime") or entry.get("createdDateTime") or ""
                    items.append(
                        TeamsTranscriptItem(
                            id=entry["id"],
                            title=name.rsplit(".", 1)[0],
                            date=modified,
                            source="onedrive",
                            file_name=name,
                        )
                    )
                url = data.get("@odata.nextLink")
        items.sort(key=lambda x: x.date, reverse=True)
        return items

    async def fetch_transcript_text(self, user, db, meeting_id: str, source: str) -> str:
        if source == "mock" or meeting_id.startswith("mock-"):
            return self._fetch_mock_transcript(meeting_id)
        return await self._fetch_onedrive_item(user, db, meeting_id)

    def _fetch_mock_transcript(self, meeting_id: str) -> str:
        path = SAMPLES_DIR / "mock_meetings.json"
        meetings = json.loads(path.read_text(encoding="utf-8"))
        match = next((m for m in meetings if m["id"] == meeting_id), None)
        if not match:
            raise ValueError(f"Mock meeting not found: {meeting_id}")
        vtt_path = SAMPLES_DIR / match["transcript_file"]
        return vtt_to_plain_text(vtt_path.read_text(encoding="utf-8"))

    async def _fetch_onedrive_item(self, user, db, item_id: str) -> str:
        token = await self._get_access_token(user, db)
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content"
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            body = resp.text
        if body.strip().upper().startswith("WEBVTT"):
            return vtt_to_plain_text(body)
        return body.strip()
