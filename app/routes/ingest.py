import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user, get_or_create_db_user
from app.database import get_db
from app.models import SessionRecord
from app.routes.sessions import _word_count
from app.schemas.session import SessionDetail
from app.services.normalize import normalize_transcript
from app.services.search_index import build_search_blob

router = APIRouter()

ALLOWED_EXTENSIONS = {".txt"}
MAX_BYTES = 2 * 1024 * 1024


@router.post("/upload", response_model=SessionDetail, status_code=201)
async def upload_transcript_file(
    file: UploadFile = File(...),
    mode: str = "meeting",
    title: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    if mode not in ("meeting", "interview"):
        raise HTTPException(400, detail="Choose mode: meeting or interview.")

    filename = file.filename or "upload.txt"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".txt"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            detail="Only .txt uploads are supported. Paste text or save your file as .txt first.",
        )

    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(400, detail="File too large (max 2 MB).")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise HTTPException(400, detail="File must be UTF-8 or Latin-1 text.") from exc

    normalized = normalize_transcript(text)
    wc = _word_count(normalized)
    if wc < 1:
        raise HTTPException(400, detail="File is empty or has no readable text.")

    user = get_or_create_db_user(db, auth)
    session_title = title or filename.rsplit(".", 1)[0] or "Uploaded session"

    session = SessionRecord(
        user_id=user.id,
        title=session_title[:500],
        mode=mode,
        source="upload",
        status="draft",
        transcript_text=normalized,
        word_count=wc,
    )
    session.search_vector = build_search_blob(session)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
