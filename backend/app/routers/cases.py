from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse
from typing import Optional
from ..models import CaseResponse, JobResponse, RtspRequest
from ..database import supabase
from ..tasks import scan_video_task, monitor_rtsp_task
import uuid
import os
import json
import base64
import requests

router = APIRouter()

ML_SERVICE_URL = os.environ.get("ML_SERVICE_URL", "http://localhost:8050")

# ── LIST ALL CASES ────────────────────────────────────────────────────
@router.get("/")
def list_cases():
    try:
        response = supabase.table("cases").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── GET SINGLE CASE ───────────────────────────────────────────────────
@router.get("/{case_id}")
def get_case(case_id: str):
    try:
        response = supabase.table("cases").select("*").eq("id", case_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Case not found")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── CREATE NEW CASE ───────────────────────────────────────────────────
@router.post("/")
async def create_case(
    case_number: str = Form(...),
    child_name: str = Form(...),
    child_age: Optional[int] = Form(None),
    last_seen_date: Optional[str] = Form(None),
    last_seen_place: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    officer_name: Optional[str] = Form(None),
    officer_contact: Optional[str] = Form(None),
    reference_photo: UploadFile = File(...)
):
    case_id = str(uuid.uuid4())

    # 1. Save the reference photo to Supabase Storage
    photo_ext = os.path.splitext(reference_photo.filename)[1] or ".jpg"
    photo_filename = f"{case_id}{photo_ext}"
    
    photo_bytes = await reference_photo.read()
    content_type = reference_photo.content_type or "image/jpeg"
    
    try:
        supabase.storage.from_("photos").upload(
            photo_filename, 
            photo_bytes,
            {"content-type": content_type}
        )
    except Exception as e:
        print(f"Failed to upload photo to Supabase: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload photo to Cloud Storage")

    public_photo_url = supabase.storage.from_("photos").get_public_url(photo_filename)

    # 2. Send photo to ML Service for ArcFace embedding extraction
    embedding_json = None
    try:
        photo_b64 = base64.b64encode(photo_bytes).decode("utf-8")
        resp = requests.post(
            f"{ML_SERVICE_URL}/extract-reference",
            json={"reference_image_b64": photo_b64},
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()
            embedding_json = result["embedding"]
        else:
            print(f"ML Service error during embedding extraction: {resp.status_code} {resp.text}")
    except requests.exceptions.RequestException as e:
        print(f"ML Service unreachable for embedding extraction: {e}")

    # 3. Insert into Supabase Postgres
    try:
        case_data = {
            "id": case_id,
            "case_number": case_number,
            "child_name": child_name,
            "child_age": child_age,
            "last_seen_date": last_seen_date,
            "last_seen_place": last_seen_place,
            "description": description,
            "officer_name": officer_name,
            "officer_contact": officer_contact,
            "reference_photo": public_photo_url,
            "face_embedding": embedding_json
        }
        resp = supabase.table("cases").insert(case_data).execute()
        case_record = resp.data[0]
        case_record["has_embedding"] = embedding_json is not None
        return case_record
    except Exception as e:
        # Rollback photo on db fail
        try: supabase.storage.from_("photos").remove([photo_filename])
        except: pass
        raise HTTPException(status_code=500, detail=f"Database Insertion Error: {str(e)}")


# ── SERVE REFERENCE PHOTO ────────────────────────────────────────────
# Retained for legacy API integration, now dynamically returning public bucket URL.
@router.get("/{case_id}/photo")
def get_case_photo(case_id: str):
    response = supabase.table("cases").select("reference_photo").eq("id", case_id).execute()
    if not response.data or not response.data[0].get("reference_photo"):
        raise HTTPException(status_code=404, detail="Photo not found")
    return RedirectResponse(url=response.data[0]["reference_photo"])


# ── UPLOAD CCTV VIDEO FOR SCANNING ───────────────────────────────────
@router.post("/{case_id}/upload")
async def upload_video(case_id: str, video_file: UploadFile = File(...)):
    # Verify case exists and has an embedding
    response = supabase.table("cases").select("id, face_embedding").eq("id", case_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case_record = response.data[0]
    if not case_record.get("face_embedding"):
        raise HTTPException(
            status_code=400, 
            detail="This case has no face embedding yet. The ML service may have been offline during case creation. Please re-upload the reference photo."
        )

    # Save video to Supabase Storage
    video_ext = os.path.splitext(video_file.filename)[1] or ".mp4"
    video_id = str(uuid.uuid4())
    video_filename = f"{video_id}{video_ext}"
    content_type = video_file.content_type or "video/mp4"

    video_bytes = await video_file.read()
    
    try:
        supabase.storage.from_("videos").upload(
            video_filename, 
            video_bytes,
            {"content-type": content_type}
        )
    except Exception as e:
        print(f"Failed to upload video to Supabase: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload video to Cloud Storage")

    public_video_url = supabase.storage.from_("videos").get_public_url(video_filename)

    # We need a local temp path for Celery to process via OpenCV since OpenCV doesn't easily process HTTP streams for processing duration.
    # Therefore we still save it temporarily explicitly for ml-service batch processing.
    STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
    VIDEOS_DIR = os.path.join(STORAGE_DIR, "videos")
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    temp_local_path = os.path.join(VIDEOS_DIR, video_filename)
    with open(temp_local_path, "wb") as f:
        f.write(video_bytes)

    # Create job record
    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,
        "case_id": case_id,
        "job_type": "scan_video",
        "video_path": public_video_url, # Reference cloud url for clients
        "status": "queued"
    }
    supabase.table("jobs").insert(job_data).execute()

    # Dispatch Celery task with local path for OpenCV logic
    reference_embedding = case_record["face_embedding"]
    try:
        scan_video_task.delay(case_id, temp_local_path, reference_embedding, job_id)
    except Exception as e:
        supabase.table("jobs").update({"status": "failed", "error_message": f"Could not dispatch task: {str(e)}"}).eq("id", job_id).execute()

    return {
        "id": job_id,
        "case_id": case_id,
        "job_type": "scan_video",
        "status": "queued",
        "progress_pct": 0,
        "error_message": None,
        "video_filename": public_video_url
    }


# ── REGISTER RTSP LIVE STREAM ────────────────────────────────────────
@router.post("/{case_id}/rtsp")
def register_rtsp(case_id: str, request: RtspRequest):
    response = supabase.table("cases").select("id, face_embedding").eq("id", case_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case_record = response.data[0]
    if not case_record.get("face_embedding"):
        raise HTTPException(status_code=400, detail="Case has no face embedding. ML service may have been offline.")

    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,
        "case_id": case_id,
        "job_type": "monitor_rtsp",
        "rtsp_url": request.rtsp_url,
        "status": "queued"
    }
    supabase.table("jobs").insert(job_data).execute()

    # Dispatch RTSP monitoring task
    reference_embedding = case_record["face_embedding"]
    try:
        monitor_rtsp_task.delay(case_id, request.rtsp_url, reference_embedding, job_id)
    except Exception as e:
        supabase.table("jobs").update({"status": "failed", "error_message": f"Could not dispatch task: {str(e)}"}).eq("id", job_id).execute()

    return {
        "id": job_id,
        "case_id": case_id,
        "job_type": "monitor_rtsp",
        "status": "queued",
        "progress_pct": 0,
        "error_message": None
    }


# ── GET MATCHES FOR A CASE ───────────────────────────────────────────
@router.get("/{case_id}/matches")
def get_matches(case_id: str):
    try:
        response = supabase.table("matches").select("*").eq("case_id", case_id).order("confidence_score", desc=True).execute()
        matches = response.data
        # Format for frontend parity
        formatted_matches = []
        for row in matches:
            formatted_matches.append({
                "id": row["id"],
                "case_id": row["case_id"],
                "video_source": row["video_source"],
                "source_type": row["source_type"],
                "timestamp_seconds": row["timestamp_seconds"],
                "timestamp_display": row["timestamp_display"],
                "frame_number": row["frame_number"],
                "confidence_score": row["confidence_score"],
                "bbox": {
                    "x1": row["bbox_x1"],
                    "y1": row["bbox_y1"],
                    "x2": row["bbox_x2"],
                    "y2": row["bbox_y2"]
                },
                "screenshot_path": row.get("screenshot_cloud") or row.get("screenshot_local"),
                "camera_id": row["camera_id"],
                "is_confirmed": bool(row["is_confirmed"]),
                "is_false_positive": bool(row["is_false_positive"]),
                "detected_at": row["detected_at"],
            })
        return formatted_matches
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── SERVE MATCH SCREENSHOT ───────────────────────────────────────────
@router.get("/{case_id}/matches/{match_id}/screenshot")
def get_match_screenshot(case_id: str, match_id: str):
    response = supabase.table("matches").select("screenshot_cloud").eq("id", match_id).eq("case_id", case_id).execute()
    if not response.data or not response.data[0].get("screenshot_cloud"):
        raise HTTPException(status_code=404, detail="Screenshot not found in cloud")
    return RedirectResponse(url=response.data[0]["screenshot_cloud"])


# ── GET JOBS FOR A CASE ──────────────────────────────────────────────
@router.get("/{case_id}/jobs")
def get_jobs(case_id: str):
    try:
        response = supabase.table("jobs").select("*").eq("case_id", case_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── DELETE A CASE ────────────────────────────────────────────────────
@router.delete("/{case_id}")
def delete_case(case_id: str):
    try:
        response = supabase.table("cases").select("id").eq("id", case_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Supabase CASCADE DELETE handles dependencies like jobs/matches.
        supabase.table("cases").delete().eq("id", case_id).execute()
        return {"status": "deleted", "case_id": case_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
