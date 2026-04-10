from celery import Celery
import os
import requests
import cv2
import base64
import uuid
import time
from datetime import datetime
from .video_utils import get_video_rotation, extract_and_normalize_frame
from .database import supabase

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ml_service_url = os.environ.get("ML_SERVICE_URL", "http://localhost:8050")

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


def _upload_screenshot(frame, case_id: str, frame_idx: int, bbox: list) -> str:
    """Draw bounding box on frame and save buffer directly to Supabase Storage."""
    screenshot = frame.copy()
    x1, y1, x2, y2 = [int(c) for c in bbox]
    cv2.rectangle(screenshot, (x1, y1), (x2, y2), (0, 255, 0), 3)
    cv2.putText(screenshot, "MATCH", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    
    filename = f"{case_id}_frame{frame_idx}_{uuid.uuid4().hex[:8]}.jpg"
    
    # Encode to memory buffer
    _, buffer = cv2.imencode('.jpg', screenshot)
    image_bytes = buffer.tobytes()
    
    try:
        supabase.storage.from_("screenshots").upload(
            filename,
            image_bytes,
            {"content-type": "image/jpeg"}
        )
    except Exception as e:
        print(f"Failed to upload screenshot to cloud: {e}")
        return ""
        
    return supabase.storage.from_("screenshots").get_public_url(filename)


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS display format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fetch_case_matches_count(case_id: str) -> int:
    try:
        resp = supabase.table("cases").select("total_matches").eq("id", case_id).execute()
        return resp.data[0]["total_matches"] if resp.data else 0
    except:
        return 0


def _fetch_case_videos_analyzed(case_id: str) -> int:
    try:
        resp = supabase.table("cases").select("videos_analyzed").eq("id", case_id).execute()
        return resp.data[0]["videos_analyzed"] if resp.data else 0
    except:
        return 0


@celery_app.task(bind=True, max_retries=3)
def scan_video_task(self, case_id: str, video_path: str, reference_embedding: list, job_id: str = None):
    """
    Slices the video using OpenCV, sends frames to the ML engine,
    and persists all matches to Supabase cloud.
    """
    try:
        if job_id:
            supabase.table("jobs").update({"status": "running", "started_at": datetime.utcnow().isoformat()}).eq("id", job_id).execute()
        
        rotation = get_video_rotation(video_path)
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            if job_id:
                supabase.table("jobs").update({"status": "failed", "error_message": "Could not open video file locally"}).eq("id", job_id).execute()
            return {"status": "failed", "case_id": case_id, "error": "Could not open video file"}
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(fps))
        
        if job_id:
            supabase.table("jobs").update({"frames_total": total_frames // frame_interval}).eq("id", job_id).execute()
        
        matches_found = 0
        frames_processed = 0
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = extract_and_normalize_frame(cap, rotation=rotation)
            if not ret:
                break
                
            if frame_idx % frame_interval == 0:
                _, buffer = cv2.imencode('.jpg', frame)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
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
                            
                            # Upload to Cloud Bucket
                            screenshot_url = _upload_screenshot(
                                frame, case_id, frame_idx, bbox
                            )
                            
                            match_id = str(uuid.uuid4())
                            match_data = {
                                "id": match_id,
                                "case_id": case_id,
                                "video_source": os.path.basename(video_path),
                                "source_type": "upload",
                                "timestamp_seconds": timestamp_sec,
                                "timestamp_display": _format_timestamp(timestamp_sec),
                                "frame_number": frame_idx,
                                "confidence_score": confidence,
                                "bbox_x1": bbox[0],
                                "bbox_y1": bbox[1],
                                "bbox_x2": bbox[2],
                                "bbox_y2": bbox[3],
                                "screenshot_cloud": screenshot_url
                            }
                            supabase.table("matches").insert(match_data).execute()
                
                except requests.exceptions.RequestException as e:
                    print(f"ML service request failed at frame {frame_idx}: {e}")
                
                frames_processed += 1
                
                if job_id and frames_processed % 10 == 0:
                    progress = min(99, int((frame_idx / max(total_frames, 1)) * 100))
                    supabase.table("jobs").update({
                        "progress_pct": progress, 
                        "frames_done": frames_processed
                    }).eq("id", job_id).execute()
                    
            frame_idx += 1
            
        cap.release()
        
        # Update case with match count and video count via direct fetch & update (since PostgREST lacks direct increment easily from SDK)
        current_matches = _fetch_case_matches_count(case_id)
        current_videos = _fetch_case_videos_analyzed(case_id)
        
        supabase.table("cases").update({
            "total_matches": current_matches + matches_found,
            "videos_analyzed": current_videos + 1,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", case_id).execute()
        
        if job_id:
            supabase.table("jobs").update({
                "status": "completed", 
                "progress_pct": 100, 
                "frames_done": frames_processed, 
                "completed_at": datetime.utcnow().isoformat()
            }).eq("id", job_id).execute()
        
        # Clean up the localized copy that OpenCV used
        try: os.remove(video_path)
        except: pass

        return {
            "status": "completed",
            "case_id": case_id,
            "matches": matches_found,
            "frames_processed": frames_processed
        }
        
    except requests.exceptions.RequestException as e:
        if job_id:
            supabase.table("jobs").update({"status": "retrying", "error_message": str(e)}).eq("id", job_id).execute()
        self.retry(exc=e, countdown=10)
        
    except Exception as e:
        if job_id:
            supabase.table("jobs").update({"status": "failed", "error_message": str(e)}).eq("id", job_id).execute()
        raise


@celery_app.task(bind=True, max_retries=3)
def monitor_rtsp_task(self, case_id: str, rtsp_url: str, reference_embedding: list, job_id: str = None):
    """
    Connects to an RTSP stream and continuously analyzes frames
    for face matches against the reference embedding, pushing to Supabase.
    """
    try:
        if job_id:
            supabase.table("jobs").update({"status": "running", "started_at": datetime.utcnow().isoformat()}).eq("id", job_id).execute()
        
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            if job_id:
                supabase.table("jobs").update({
                    "status": "failed", 
                    "error_message": f"Could not connect to RTSP stream: {rtsp_url}"
                }).eq("id", job_id).execute()
            return {"status": "failed", "case_id": case_id, "error": "Could not connect to RTSP stream"}
        
        frame_idx = 0
        matches_found = 0
        fps = cap.get(cv2.CAP_PROP_FPS) or 15
        frame_interval = max(1, int(fps))
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                time.sleep(2)
                cap.release()
                cap = cv2.VideoCapture(rtsp_url)
                if not cap.isOpened():
                    break
                continue
            
            if frame_idx % frame_interval == 0:
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
                            
                            screenshot_url = _upload_screenshot(
                                frame, case_id, frame_idx, bbox
                            )
                            
                            match_id = str(uuid.uuid4())
                            match_data = {
                                "id": match_id,
                                "case_id": case_id,
                                "video_source": rtsp_url,
                                "source_type": "rtsp",
                                "timestamp_seconds": timestamp_sec,
                                "timestamp_display": _format_timestamp(timestamp_sec),
                                "frame_number": frame_idx,
                                "confidence_score": confidence,
                                "bbox_x1": bbox[0],
                                "bbox_y1": bbox[1],
                                "bbox_x2": bbox[2],
                                "bbox_y2": bbox[3],
                                "screenshot_cloud": screenshot_url,
                                "camera_id": rtsp_url
                            }
                            supabase.table("matches").insert(match_data).execute()
                            
                            current_matches = _fetch_case_matches_count(case_id)
                            supabase.table("cases").update({
                                "total_matches": current_matches + 1,
                                "updated_at": datetime.utcnow().isoformat()
                            }).eq("id", case_id).execute()
                
                except requests.exceptions.RequestException:
                    pass 
            
            frame_idx += 1
        
        cap.release()
        
        if job_id:
            supabase.table("jobs").update({"status": "completed", "completed_at": datetime.utcnow().isoformat()}).eq("id", job_id).execute()
        
        return {"status": "completed", "case_id": case_id, "matches": matches_found}
        
    except Exception as e:
        if job_id:
            supabase.table("jobs").update({"status": "failed", "error_message": str(e)}).eq("id", job_id).execute()
        raise
