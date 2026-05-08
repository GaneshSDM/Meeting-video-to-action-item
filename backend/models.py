from pydantic import BaseModel
from typing import List, Optional

class ActionItem(BaseModel):
    owner: str
    task: str

class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int
    result: Optional[str] = None
    error: Optional[str] = None
