from pydantic import BaseModel
from typing import Optional, List

class CaseCreate(BaseModel):
    case_number: str
    child_name: str
    child_age: Optional[int] = None
    last_seen_date: Optional[str] = None
    last_seen_place: Optional[str] = None
    description: Optional[str] = None
    officer_name: Optional[str] = None
    officer_contact: Optional[str] = None

class CaseResponse(CaseCreate):
    id: str
    status: str
    total_matches: int
    videos_analyzed: int
    created_at: str
    updated_at: str
    
class JobResponse(BaseModel):
    id: str
    case_id: str
    job_type: str
    status: str
    progress_pct: int
    error_message: Optional[str] = None

class RtspRequest(BaseModel):
    camera_name: str
    rtsp_url: str
    alert_threshold: Optional[float] = 0.68
