from celery import Celery
import os
import requests
import cv2
import base64
from .video_utils import get_video_rotation, extract_and_normalize_frame

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ml_service_url = os.environ.get("ML_SERVICE_URL", "http://localhost:8080")

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

@celery_app.task(bind=True, max_retries=3)
def scan_video_task(self, case_id: str, video_path: str, reference_embedding: list):
    """
    Slices the video using OpenCV, formats it securely, and pipelines it securely to the ML engine 
    deployed on Google Cloud (or locally). Focuses primarily on mobile phone metadata configurations.
    """
    try:
        rotation = get_video_rotation(video_path)
        cap = cv2.VideoCapture(video_path)
        
        matches_found = 0
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = extract_and_normalize_frame(cap, rotation=rotation)
            if not ret:
                break
                
            # Process 1 frame per second (assuming 30fps)
            if frame_idx % 30 == 0:
                # Convert frame to Base64 for the ML HTTP REST Service
                _, buffer = cv2.imencode('.jpg', frame)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                # Ping the Cloud GPU ML Engine!
                response = requests.post(f"{ml_service_url}/analyze", json={
                    "frame_b64": str(frame_b64),
                    "reference_embedding": reference_embedding
                })
                
                if response.status_code == 200:
                    result = response.json()
                    matches = result.get("matches", [])
                    if matches:
                        matches_found += len(matches)
                        # Here: save screenshot locally, update SQLite DB, etc.
                        # (We'll wire up the SQLite insertions fully in Phase 3)
                        
            frame_idx += 1
            
        cap.release()
        return {"status": "completed", "case_id": case_id, "matches": matches_found}
        
    except requests.exceptions.RequestException as e:
        # Retry the task if the ML service drops connection remotely
        self.retry(exc=e, countdown=10)
        
@celery_app.task
def monitor_rtsp_task(case_id: str, rtsp_url: str):
    # Dummy implementation - Will utilize the exact same frame extractor loop logic!
    return {"status": "monitoring", "case_id": case_id, "rtsp_url": rtsp_url}
