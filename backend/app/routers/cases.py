from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from ..models import CaseResponse, JobResponse, RtspRequest
from ..database import get_db_connection
from ..tasks import scan_video_task, monitor_rtsp_task
import uuid
import os
import json
import base64
import requests
import aiosqlite

router = APIRouter()

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
PHOTOS_DIR = os.path.join(STORAGE_DIR, "photos")
VIDEOS_DIR = os.path.join(STORAGE_DIR, "videos")
SCREENSHOTS_DIR = os.path.join(STORAGE_DIR, "screenshots")

# Ensure storage directories exist
for d in [PHOTOS_DIR, VIDEOS_DIR, SCREENSHOTS_DIR]:
    os.makedirs(d, exist_ok=True)

ML_SERVICE_URL = os.environ.get("ML_SERVICE_URL", "http://localhost:8050")


# ── LIST ALL CASES ────────────────────────────────────────────────────
@router.get("/")
async def list_cases():
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            "SELECT * FROM cases ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        cases = []
        for row in rows:
            cases.append({
                "id": row["id"],
                "case_number": row["case_number"],
                "child_name": row["child_name"],
                "child_age": row["child_age"],
                "last_seen_date": row["last_seen_date"],
                "last_seen_place": row["last_seen_place"],
                "description": row["description"],
                "officer_name": row["officer_name"],
                "officer_contact": row["officer_contact"],
                "status": row["status"],
                "reference_photo": row["reference_photo"],
                "total_matches": row["total_matches"],
                "videos_analyzed": row["videos_analyzed"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        return cases
    finally:
        await db.close()


# ── GET SINGLE CASE ───────────────────────────────────────────────────
@router.get("/{case_id}")
async def get_case(case_id: str):
    db = await get_db_connection()
    try:
        cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Case not found")
        return {
            "id": row["id"],
            "case_number": row["case_number"],
            "child_name": row["child_name"],
            "child_age": row["child_age"],
            "last_seen_date": row["last_seen_date"],
            "last_seen_place": row["last_seen_place"],
            "description": row["description"],
            "officer_name": row["officer_name"],
            "officer_contact": row["officer_contact"],
            "status": row["status"],
            "reference_photo": row["reference_photo"],
            "total_matches": row["total_matches"],
            "videos_analyzed": row["videos_analyzed"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    finally:
        await db.close()


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

    # 1. Save the reference photo to disk
    photo_ext = os.path.splitext(reference_photo.filename)[1] or ".jpg"
    photo_filename = f"{case_id}{photo_ext}"
    photo_path = os.path.join(PHOTOS_DIR, photo_filename)
    
    photo_bytes = await reference_photo.read()
    with open(photo_path, "wb") as f:
        f.write(photo_bytes)

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
            embedding_json = json.dumps(result["embedding"])
        else:
            # ML service returned an error — store case anyway but without embedding
            print(f"ML Service error during embedding extraction: {resp.status_code} {resp.text}")
    except requests.exceptions.RequestException as e:
        # ML service unreachable — store case anyway, embedding can be retried later
        print(f"ML Service unreachable for embedding extraction: {e}")

    # 3. Insert into SQLite
    db = await get_db_connection()
    try:
        await db.execute(
            """INSERT INTO cases (id, case_number, child_name, child_age, last_seen_date, 
               last_seen_place, description, officer_name, officer_contact, reference_photo, face_embedding)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (case_id, case_number, child_name, child_age, last_seen_date,
             last_seen_place, description, officer_name, officer_contact,
             photo_filename, embedding_json)
        )
        await db.commit()

        # Read back the inserted case
        cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        return {
            "id": row["id"],
            "case_number": row["case_number"],
            "child_name": row["child_name"],
            "child_age": row["child_age"],
            "last_seen_date": row["last_seen_date"],
            "last_seen_place": row["last_seen_place"],
            "description": row["description"],
            "officer_name": row["officer_name"],
            "officer_contact": row["officer_contact"],
            "status": row["status"],
            "reference_photo": row["reference_photo"],
            "total_matches": row["total_matches"],
            "videos_analyzed": row["videos_analyzed"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "has_embedding": embedding_json is not None
        }
    finally:
        await db.close()


# ── SERVE REFERENCE PHOTO ────────────────────────────────────────────
@router.get("/{case_id}/photo")
async def get_case_photo(case_id: str):
    db = await get_db_connection()
    try:
        cursor = await db.execute("SELECT reference_photo FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        if not row or not row["reference_photo"]:
            raise HTTPException(status_code=404, detail="Photo not found")
        photo_path = os.path.join(PHOTOS_DIR, row["reference_photo"])
        if not os.path.exists(photo_path):
            raise HTTPException(status_code=404, detail="Photo file missing from disk")
        return FileResponse(photo_path)
    finally:
        await db.close()


# ── UPLOAD CCTV VIDEO FOR SCANNING ───────────────────────────────────
@router.post("/{case_id}/upload")
async def upload_video(case_id: str, video_file: UploadFile = File(...)):
    # Verify case exists and has an embedding
    db = await get_db_connection()
    try:
        cursor = await db.execute("SELECT id, face_embedding FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Case not found")
        if not row["face_embedding"]:
            raise HTTPException(
                status_code=400, 
                detail="This case has no face embedding yet. The ML service may have been offline during case creation. Please re-upload the reference photo."
            )

        # Save video to disk
        video_ext = os.path.splitext(video_file.filename)[1] or ".mp4"
        video_id = str(uuid.uuid4())
        video_filename = f"{video_id}{video_ext}"
        video_path = os.path.join(VIDEOS_DIR, video_filename)

        video_bytes = await video_file.read()
        with open(video_path, "wb") as f:
            f.write(video_bytes)

        # Create job record
        job_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO jobs (id, case_id, job_type, video_path, status)
               VALUES (?, ?, ?, ?, ?)""",
            (job_id, case_id, "scan_video", video_path, "queued")
        )
        await db.commit()

        # Dispatch Celery task
        reference_embedding = json.loads(row["face_embedding"])
        try:
            scan_video_task.delay(case_id, video_path, reference_embedding, job_id)
        except Exception as e:
            # If Celery/Redis is down, update the job status
            await db.execute(
                "UPDATE jobs SET status = ?, error_message = ? WHERE id = ?",
                ("failed", f"Could not dispatch task: {str(e)}", job_id)
            )
            await db.commit()

        return {
            "id": job_id,
            "case_id": case_id,
            "job_type": "scan_video",
            "status": "queued",
            "progress_pct": 0,
            "error_message": None,
            "video_filename": video_filename
        }
    finally:
        await db.close()


# ── REGISTER RTSP LIVE STREAM ────────────────────────────────────────
@router.post("/{case_id}/rtsp")
async def register_rtsp(case_id: str, request: RtspRequest):
    db = await get_db_connection()
    try:
        cursor = await db.execute("SELECT id, face_embedding FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Case not found")
        if not row["face_embedding"]:
            raise HTTPException(status_code=400, detail="Case has no face embedding. ML service may have been offline.")

        job_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO jobs (id, case_id, job_type, rtsp_url, status)
               VALUES (?, ?, ?, ?, ?)""",
            (job_id, case_id, "monitor_rtsp", request.rtsp_url, "queued")
        )
        await db.commit()

        # Dispatch RTSP monitoring task
        reference_embedding = json.loads(row["face_embedding"])
        try:
            monitor_rtsp_task.delay(case_id, request.rtsp_url, reference_embedding, job_id)
        except Exception as e:
            await db.execute(
                "UPDATE jobs SET status = ?, error_message = ? WHERE id = ?",
                ("failed", f"Could not dispatch task: {str(e)}", job_id)
            )
            await db.commit()

        return {
            "id": job_id,
            "case_id": case_id,
            "job_type": "monitor_rtsp",
            "status": "queued",
            "progress_pct": 0,
            "error_message": None
        }
    finally:
        await db.close()


# ── GET MATCHES FOR A CASE ───────────────────────────────────────────
@router.get("/{case_id}/matches")
async def get_matches(case_id: str):
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            """SELECT * FROM matches WHERE case_id = ? 
               ORDER BY confidence_score DESC""",
            (case_id,)
        )
        rows = await cursor.fetchall()
        matches = []
        for row in rows:
            matches.append({
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
                "screenshot_path": row["screenshot_local"],
                "camera_id": row["camera_id"],
                "is_confirmed": bool(row["is_confirmed"]),
                "is_false_positive": bool(row["is_false_positive"]),
                "detected_at": row["detected_at"],
            })
        return matches
    finally:
        await db.close()


# ── SERVE MATCH SCREENSHOT ───────────────────────────────────────────
@router.get("/{case_id}/matches/{match_id}/screenshot")
async def get_match_screenshot(case_id: str, match_id: str):
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            "SELECT screenshot_local FROM matches WHERE id = ? AND case_id = ?",
            (match_id, case_id)
        )
        row = await cursor.fetchone()
        if not row or not row["screenshot_local"]:
            raise HTTPException(status_code=404, detail="Screenshot not found")
        if not os.path.exists(row["screenshot_local"]):
            raise HTTPException(status_code=404, detail="Screenshot file missing from disk")
        return FileResponse(row["screenshot_local"])
    finally:
        await db.close()


# ── GET JOBS FOR A CASE ──────────────────────────────────────────────
@router.get("/{case_id}/jobs")
async def get_jobs(case_id: str):
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE case_id = ? ORDER BY created_at DESC",
            (case_id,)
        )
        rows = await cursor.fetchall()
        jobs = []
        for row in rows:
            jobs.append({
                "id": row["id"],
                "case_id": row["case_id"],
                "job_type": row["job_type"],
                "status": row["status"],
                "progress_pct": row["progress_pct"],
                "frames_total": row["frames_total"],
                "frames_done": row["frames_done"],
                "error_message": row["error_message"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "created_at": row["created_at"],
            })
        return jobs
    finally:
        await db.close()


# ── DELETE A CASE ────────────────────────────────────────────────────
@router.delete("/{case_id}")
async def delete_case(case_id: str):
    db = await get_db_connection()
    try:
        cursor = await db.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Case not found")
        
        await db.execute("DELETE FROM matches WHERE case_id = ?", (case_id,))
        await db.execute("DELETE FROM jobs WHERE case_id = ?", (case_id,))
        await db.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        await db.commit()
        return {"status": "deleted", "case_id": case_id}
    finally:
        await db.close()
