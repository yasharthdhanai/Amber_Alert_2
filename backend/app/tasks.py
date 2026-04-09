from celery import Celery
import os
import requests
import cv2
import base64
import uuid
import sqlite3
import time
from datetime import datetime
from .video_utils import get_video_rotation, extract_and_normalize_frame

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ml_service_url = os.environ.get("ML_SERVICE_URL", "http://localhost:8050")

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
DB_PATH = os.path.join(STORAGE_DIR, "mcf.db")
SCREENSHOTS_DIR = os.path.join(STORAGE_DIR, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

celery_app = Celery(
    "mcf_tasks",
    broker=redis_url,
    backend=redis_url
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


def _get_sync_db():
    """Get a synchronous SQLite connection for use inside Celery tasks."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _save_screenshot(frame, case_id: str, frame_idx: int, bbox: list) -> str:
    """Draw bounding box on frame and save as screenshot. Returns file path."""
    screenshot = frame.copy()
    x1, y1, x2, y2 = [int(c) for c in bbox]
    cv2.rectangle(screenshot, (x1, y1), (x2, y2), (0, 255, 0), 3)
    cv2.putText(screenshot, "MATCH", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    
    filename = f"{case_id}_frame{frame_idx}_{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)
    cv2.imwrite(filepath, screenshot)
    return filepath


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS display format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


@celery_app.task(bind=True, max_retries=3)
def scan_video_task(self, case_id: str, video_path: str, reference_embedding: list, job_id: str = None):
    """
    Slices the video using OpenCV, sends frames to the ML engine,
    and persists all matches to SQLite with annotated screenshots.
    """
    db = _get_sync_db()
    
    try:
        # Mark job as running
        if job_id:
            db.execute(
                "UPDATE jobs SET status = ?, started_at = ? WHERE id = ?",
                ("running", datetime.utcnow().isoformat(), job_id)
            )
            db.commit()
        
        rotation = get_video_rotation(video_path)
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            if job_id:
                db.execute(
                    "UPDATE jobs SET status = ?, error_message = ? WHERE id = ?",
                    ("failed", "Could not open video file", job_id)
                )
                db.commit()
            return {"status": "failed", "case_id": case_id, "error": "Could not open video file"}
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(fps))  # Process ~1 frame per second
        
        # Update job with total frame count
        if job_id:
            db.execute(
                "UPDATE jobs SET frames_total = ? WHERE id = ?",
                (total_frames // frame_interval, job_id)
            )
            db.commit()
        
        matches_found = 0
        frames_processed = 0
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = extract_and_normalize_frame(cap, rotation=rotation)
            if not ret:
                break
                
            if frame_idx % frame_interval == 0:
                # Convert frame to Base64 for the ML HTTP REST Service
                _, buffer = cv2.imencode('.jpg', frame)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                # Send to GPU ML Engine
                try:
                    response = requests.post(f"{ml_service_url}/analyze", json={
                        "frame_b64": frame_b64,
                        "reference_embedding": reference_embedding
                    }, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        matches = result.get("matches", [])
                        
                        for match in matches:
                            matches_found += 1
                            confidence = match["confidence"]
                            bbox = match["bbox"]
                            timestamp_sec = frame_idx / fps
                            
                            # Save annotated screenshot
                            screenshot_path = _save_screenshot(
                                frame, case_id, frame_idx, bbox
                            )
                            
                            # Insert match record into SQLite
                            match_id = str(uuid.uuid4())
                            db.execute(
                                """INSERT INTO matches 
                                   (id, case_id, video_source, source_type, timestamp_seconds,
                                    timestamp_display, frame_number, confidence_score,
                                    bbox_x1, bbox_y1, bbox_x2, bbox_y2, screenshot_local)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (match_id, case_id, os.path.basename(video_path), "upload",
                                 timestamp_sec, _format_timestamp(timestamp_sec), frame_idx,
                                 confidence, bbox[0], bbox[1], bbox[2], bbox[3],
                                 screenshot_path)
                            )
                            db.commit()
                
                except requests.exceptions.RequestException as e:
                    print(f"ML service request failed at frame {frame_idx}: {e}")
                    # Continue processing — don't abort the entire video for one frame failure
                
                frames_processed += 1
                
                # Update job progress every 10 frames
                if job_id and frames_processed % 10 == 0:
                    progress = min(99, int((frame_idx / max(total_frames, 1)) * 100))
                    db.execute(
                        "UPDATE jobs SET progress_pct = ?, frames_done = ? WHERE id = ?",
                        (progress, frames_processed, job_id)
                    )
                    db.commit()
                    
            frame_idx += 1
            
        cap.release()
        
        # Update case with match count and video count
        db.execute(
            """UPDATE cases SET 
               total_matches = total_matches + ?,
               videos_analyzed = videos_analyzed + 1,
               updated_at = datetime('now')
               WHERE id = ?""",
            (matches_found, case_id)
        )
        
        # Mark job as completed
        if job_id:
            db.execute(
                """UPDATE jobs SET status = ?, progress_pct = 100, 
                   frames_done = ?, completed_at = ? WHERE id = ?""",
                ("completed", frames_processed, datetime.utcnow().isoformat(), job_id)
            )
        
        db.commit()
        return {
            "status": "completed",
            "case_id": case_id,
            "matches": matches_found,
            "frames_processed": frames_processed
        }
        
    except requests.exceptions.RequestException as e:
        # Retry the task if the ML service drops connection catastrophically
        if job_id:
            db.execute(
                "UPDATE jobs SET status = ?, error_message = ? WHERE id = ?",
                ("retrying", str(e), job_id)
            )
            db.commit()
        self.retry(exc=e, countdown=10)
        
    except Exception as e:
        if job_id:
            db.execute(
                "UPDATE jobs SET status = ?, error_message = ? WHERE id = ?",
                ("failed", str(e), job_id)
            )
            db.commit()
        raise
        
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def monitor_rtsp_task(self, case_id: str, rtsp_url: str, reference_embedding: list, job_id: str = None):
    """
    Connects to an RTSP stream and continuously analyzes frames
    for face matches against the reference embedding.
    """
    db = _get_sync_db()
    
    try:
        if job_id:
            db.execute(
                "UPDATE jobs SET status = ?, started_at = ? WHERE id = ?",
                ("running", datetime.utcnow().isoformat(), job_id)
            )
            db.commit()
        
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            if job_id:
                db.execute(
                    "UPDATE jobs SET status = ?, error_message = ? WHERE id = ?",
                    ("failed", f"Could not connect to RTSP stream: {rtsp_url}", job_id)
                )
                db.commit()
            return {"status": "failed", "case_id": case_id, "error": "Could not connect to RTSP stream"}
        
        frame_idx = 0
        matches_found = 0
        fps = cap.get(cv2.CAP_PROP_FPS) or 15
        frame_interval = max(1, int(fps))  # ~1 frame per second
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                # Stream may have ended or disconnected
                time.sleep(2)
                cap.release()
                cap = cv2.VideoCapture(rtsp_url)
                if not cap.isOpened():
                    break
                continue
            
            if frame_idx % frame_interval == 0:
                # Resize for transmission efficiency
                h, w = frame.shape[:2]
                if w > 640:
                    ratio = 640 / w
                    frame = cv2.resize(frame, (640, int(h * ratio)), interpolation=cv2.INTER_AREA)
                
                _, buffer = cv2.imencode('.jpg', frame)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                try:
                    response = requests.post(f"{ml_service_url}/analyze", json={
                        "frame_b64": frame_b64,
                        "reference_embedding": reference_embedding
                    }, timeout=15)
                    
                    if response.status_code == 200:
                        result = response.json()
                        matches = result.get("matches", [])
                        
                        for match in matches:
                            matches_found += 1
                            confidence = match["confidence"]
                            bbox = match["bbox"]
                            timestamp_sec = frame_idx / fps
                            
                            screenshot_path = _save_screenshot(
                                frame, case_id, frame_idx, bbox
                            )
                            
                            match_id = str(uuid.uuid4())
                            db.execute(
                                """INSERT INTO matches 
                                   (id, case_id, video_source, source_type, timestamp_seconds,
                                    timestamp_display, frame_number, confidence_score,
                                    bbox_x1, bbox_y1, bbox_x2, bbox_y2, screenshot_local,
                                    camera_id)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (match_id, case_id, rtsp_url, "rtsp",
                                 timestamp_sec, _format_timestamp(timestamp_sec), frame_idx,
                                 confidence, bbox[0], bbox[1], bbox[2], bbox[3],
                                 screenshot_path, rtsp_url)
                            )
                            
                            # Update case match count
                            db.execute(
                                """UPDATE cases SET total_matches = total_matches + 1,
                                   updated_at = datetime('now') WHERE id = ?""",
                                (case_id,)
                            )
                            db.commit()
                
                except requests.exceptions.RequestException:
                    pass  # Continue monitoring even if one frame fails
            
            frame_idx += 1
        
        cap.release()
        
        if job_id:
            db.execute(
                """UPDATE jobs SET status = ?, completed_at = ? WHERE id = ?""",
                ("completed", datetime.utcnow().isoformat(), job_id)
            )
            db.commit()
        
        return {"status": "completed", "case_id": case_id, "matches": matches_found}
        
    except Exception as e:
        if job_id:
            db.execute(
                "UPDATE jobs SET status = ?, error_message = ? WHERE id = ?",
                ("failed", str(e), job_id)
            )
            db.commit()
        raise
        
    finally:
        db.close()
