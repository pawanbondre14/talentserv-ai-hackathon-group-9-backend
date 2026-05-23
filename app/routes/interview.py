from fastapi import APIRouter, Depends

from app.auth import AuthUser, get_current_user
from app.config import Settings, get_settings
from app.schemas.interview import PanelMergeRequest, ScorecardTemplate
from app.services.interview_processor import process_interview
from app.services.scorecards import list_scorecards

router = APIRouter()


@router.get("/scorecards", response_model=list[ScorecardTemplate])
def get_scorecards(_auth: AuthUser = Depends(get_current_user)):
    return list_scorecards()


@router.post("/panel-merge")
def merge_panel_transcripts(
    body: PanelMergeRequest,
    settings: Settings = Depends(get_settings),
    _auth: AuthUser = Depends(get_current_user),
):
    """Preview consolidated panel feedback without creating a session."""
    from app.schemas.interview import InterviewProcessOptions

    primary, *rest = body.transcripts
    options = InterviewProcessOptions(
        jd_text=body.jd_text,
        scorecard_id=body.scorecard_id,
        blind_mode=body.blind_mode,
        panel_transcripts=rest if rest else None,
    )
    return process_interview(settings, primary, options)
