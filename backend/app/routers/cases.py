from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import Optional
from ..models import CaseCreate, CaseResponse, RtspRequest, JobResponse
import uuid

router = APIRouter()

@router.post("/", response_model=CaseResponse)
async def create_case(
    case_number: str = Form(...),
    child_name: str = Form(...),
    child_age: Optional[int] = Form(None),
    reference_photo: UploadFile = File(...)
):
    # Dummy implementation for scaffolding
    case_id = str(uuid.uuid4())
    return {
        "id": case_id,
        "case_number": case_number,
        "child_name": child_name,
        "child_age": child_age,
        "status": "active",
        "total_matches": 0,
        "videos_analyzed": 0,
        "created_at": "now",
        "updated_at": "now"
    }

@router.post("/{case_id}/upload", response_model=JobResponse)
async def upload_video(case_id: str, video_file: UploadFile = File(...)):
    # Dummy implementation
    job_id = str(uuid.uuid4())
    return {
        "id": job_id,
        "case_id": case_id,
        "job_type": "scan_video",
        "status": "queued",
        "progress_pct": 0
    }

@router.post("/{case_id}/rtsp", response_model=JobResponse)
async def register_rtsp(case_id: str, request: RtspRequest):
    # Dummy implementation
    job_id = str(uuid.uuid4())
    return {
        "id": job_id,
        "case_id": case_id,
        "job_type": "monitor_rtsp",
        "status": "queued",
        "progress_pct": 0
    }
