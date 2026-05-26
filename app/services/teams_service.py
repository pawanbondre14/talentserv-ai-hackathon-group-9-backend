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
ALLOWED_EXTENSIONS = {".txt", ".vtt"}
MAX_ONEDRIVE_BYTES = 10 * 1024 * 1024
MOCK_RECORDINGS_FOLDER_ID = "mock-recordings"


@dataclass
class TeamsTranscriptItem:
    id: str
    title: str
    date: str
    source: str  # mock | onedrive
    file_name: str | None = None


@dataclass
class OneDriveBrowseItemData:
    id: str
    name: str
    kind: str  # folder | file
    size: int | None = None
    modified_at: str | None = None
    extension: str | None = None


@dataclass
class OneDriveBrowseResult:
    folder_id: str
    folder_name: str
    items: list[OneDriveBrowseItemData]
    integration_mode: str


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

    @staticmethod
    def _file_extension(name: str) -> str | None:
        if "." not in name:
            return None
        return "." + name.rsplit(".", 1)[-1].lower()

    @classmethod
    def _is_eligible_file(cls, name: str) -> bool:
        lower = name.lower()
        ext = cls._file_extension(name)
        return ext in ALLOWED_EXTENSIONS or "transcript" in lower

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

    async def browse_folder(self, user, db, folder_id: str) -> OneDriveBrowseResult:
        normalized_id = folder_id or "root"
        if normalized_id == "recordings":
            if self._use_live(user):
                try:
                    return await self._browse_onedrive_recordings_folder(user, db)
                except Exception as exc:
                    logger.warning("OneDrive recordings browse failed, falling back to mock: %s", exc)
            return self._browse_mock(MOCK_RECORDINGS_FOLDER_ID)
        if self._use_live(user):
            try:
                return await self._browse_onedrive_folder(user, db, normalized_id)
            except Exception as exc:
                logger.warning("OneDrive browse failed, falling back to mock: %s", exc)
        return self._browse_mock(normalized_id)

    def _browse_mock(self, folder_id: str) -> OneDriveBrowseResult:
        if folder_id == MOCK_RECORDINGS_FOLDER_ID:
            items = [
                OneDriveBrowseItemData(
                    id=m.id,
                    name=m.file_name or f"{m.title}.vtt",
                    kind="file",
                    modified_at=m.date,
                    extension=self._file_extension(m.file_name or ""),
                )
                for m in self._list_mock()
            ]
            return OneDriveBrowseResult(
                folder_id=MOCK_RECORDINGS_FOLDER_ID,
                folder_name="Recordings",
                items=items,
                integration_mode="mock",
            )

        return OneDriveBrowseResult(
            folder_id="root",
            folder_name="OneDrive",
            items=[
                OneDriveBrowseItemData(
                    id=MOCK_RECORDINGS_FOLDER_ID,
                    name="Recordings",
                    kind="folder",
                ),
            ],
            integration_mode="mock",
        )

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

    async def _graph_list_children(self, user, db, url: str) -> list[dict]:
        token = await self._get_access_token(user, db)
        headers = {"Authorization": f"Bearer {token}"}
        entries: list[dict] = []
        async with httpx.AsyncClient(timeout=30) as client:
            while url:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                entries.extend(data.get("value", []))
                url = data.get("@odata.nextLink")
        return entries

    def _entries_to_browse_items(self, entries: list[dict]) -> list[OneDriveBrowseItemData]:
        items: list[OneDriveBrowseItemData] = []
        for entry in entries:
            name = entry.get("name", "")
            if "folder" in entry:
                items.append(
                    OneDriveBrowseItemData(
                        id=entry["id"],
                        name=name,
                        kind="folder",
                        modified_at=entry.get("lastModifiedDateTime")
                        or entry.get("createdDateTime"),
                    )
                )
            elif "file" in entry and self._is_eligible_file(name):
                items.append(
                    OneDriveBrowseItemData(
                        id=entry["id"],
                        name=name,
                        kind="file",
                        size=entry.get("size"),
                        modified_at=entry.get("lastModifiedDateTime")
                        or entry.get("createdDateTime"),
                        extension=self._file_extension(name),
                    )
                )
        folders = [i for i in items if i.kind == "folder"]
        files = [i for i in items if i.kind == "file"]
        folders.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())
        return folders + files

    async def _browse_onedrive_recordings_folder(self, user, db) -> OneDriveBrowseResult:
        url = "https://graph.microsoft.com/v1.0/me/drive/root:/Recordings:/children"
        entries = await self._graph_list_children(user, db, url)
        return OneDriveBrowseResult(
            folder_id="recordings",
            folder_name="Recordings",
            items=self._entries_to_browse_items(entries),
            integration_mode="live",
        )

    async def _browse_onedrive_folder(self, user, db, folder_id: str) -> OneDriveBrowseResult:
        if folder_id == "root":
            url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
            folder_name = "OneDrive"
        else:
            meta_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}"
            token = await self._get_access_token(user, db)
            async with httpx.AsyncClient(timeout=30) as client:
                meta_resp = await client.get(
                    meta_url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                meta_resp.raise_for_status()
                meta = meta_resp.json()
            folder_name = meta.get("name", "Folder")
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children"

        entries = await self._graph_list_children(user, db, url)
        return OneDriveBrowseResult(
            folder_id=folder_id,
            folder_name=folder_name,
            items=self._entries_to_browse_items(entries),
            integration_mode="live",
        )

    async def _list_onedrive_recordings(self, user, db) -> list[TeamsTranscriptItem]:
        url = "https://graph.microsoft.com/v1.0/me/drive/root:/Recordings:/children"
        entries = await self._graph_list_children(user, db, url)
        items: list[TeamsTranscriptItem] = []
        for entry in entries:
            name = entry.get("name", "")
            if not self._is_eligible_file(name):
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
        meta_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
        async with httpx.AsyncClient(timeout=30) as client:
            meta_resp = await client.get(meta_url, headers=headers)
            meta_resp.raise_for_status()
            meta = meta_resp.json()
            size = meta.get("size") or 0
            if size > MAX_ONEDRIVE_BYTES:
                raise ValueError(
                    f"File too large ({size // (1024 * 1024)}MB). Max is {MAX_ONEDRIVE_BYTES // (1024 * 1024)}MB."
                )

        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content"
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            body = resp.text
        if body.strip().upper().startswith("WEBVTT"):
            return vtt_to_plain_text(body)
        return body.strip()

    @staticmethod
    def parse_file_text(body: str) -> str:
        if body.strip().upper().startswith("WEBVTT"):
            return vtt_to_plain_text(body)
        return body.strip()
