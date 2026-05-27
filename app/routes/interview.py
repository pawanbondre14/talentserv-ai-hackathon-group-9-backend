from fastapi import APIRouter, Depends

from app.constants.permissions import INTERVIEW_PROCESS, INTERVIEW_READ
from app.config import Settings, get_settings
from app.dependencies.authz import Principal, require_permission
from app.schemas.interview import PanelMergeRequest, ScorecardTemplate
from app.services.interview_processor import process_interview
from app.services.scorecards import list_scorecards

router = APIRouter()


@router.get("/scorecards", response_model=list[ScorecardTemplate])
def get_scorecards(_principal: Principal = Depends(require_permission(INTERVIEW_READ))):
    return list_scorecards()


@router.post("/panel-merge")
def merge_panel_transcripts(
    body: PanelMergeRequest,
    settings: Settings = Depends(get_settings),
    _principal: Principal = Depends(require_permission(INTERVIEW_PROCESS)),
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
