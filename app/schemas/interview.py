from pydantic import BaseModel, Field


class InterviewProcessOptions(BaseModel):
    jd_text: str | None = None
    scorecard_id: str | None = None
    blind_mode: bool = False
    candidate_name: str | None = None
    candidate_email: str | None = None
    panel_transcripts: list[str] | None = Field(
        default=None,
        description="Additional interviewer transcripts to merge before analysis",
    )


class ProcessRequest(BaseModel):
    interview_options: InterviewProcessOptions | None = None


class ScorecardCriterion(BaseModel):
    id: str
    label: str
    weight: float = 1.0


class ScorecardTemplate(BaseModel):
    id: str
    title: str
    criteria: list[ScorecardCriterion]


class PanelMergeRequest(BaseModel):
    transcripts: list[str] = Field(..., min_length=2, max_length=5)
    jd_text: str | None = None
    scorecard_id: str | None = None
    blind_mode: bool = False


class InterviewMetaOut(BaseModel):
    jd_text: str | None = None
    scorecard_id: str | None = None
    blind_mode: bool = False
    candidate_name: str | None = None
    candidate_email: str | None = None

    model_config = {"from_attributes": True}
