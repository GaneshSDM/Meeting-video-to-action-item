from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Any


class ActionItem(BaseModel):
    owner: str = "Unknown"
    task: str = ""
    deadline: Optional[str] = None
    priority: Literal["high", "medium", "low"] = "medium"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    context: Optional[str] = None

    @field_validator("owner", mode="before")
    @classmethod
    def coerce_owner(cls, v: Any) -> str:
        return v if isinstance(v, str) and v else "Unknown"

    @field_validator("task", mode="before")
    @classmethod
    def coerce_task(cls, v: Any) -> str:
        return v if isinstance(v, str) and v else ""


class AnalysisRequest(BaseModel):
    sharepoint_url: str


class AnalysisOutput(BaseModel):
    transcript: Optional[str] = None
    meeting_summary: Optional[str] = None
    participants: List[str] = []
    action_items: List[ActionItem] = []
    raw_result: Optional[str] = None

    @field_validator("action_items", mode="after")
    @classmethod
    def filter_empty(cls, v: List[ActionItem]) -> List[ActionItem]:
        return [item for item in v if item.task]


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int
    result: Optional[AnalysisOutput] = None
    error: Optional[str] = None


class ExportRequest(BaseModel):
    target: Literal["sharepoint_list", "sharepoint_document", "local_log"]
    sharepoint_url: Optional[str] = None
