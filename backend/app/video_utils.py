import cv2
import numpy as np
import subprocess
import json

def get_video_rotation(video_path: str) -> int:
    """
    Attempts to read rotation metadata from video using ffprobe.
    Many phone videos are saved horizontally with a rotation flag.
    Requires ffprobe installed locally.
    """
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                tags = stream.get("tags", {})
                if "rotate" in tags:
                    return int(tags["rotate"])
    except Exception:
        pass
    return 0

def apply_rotation(frame: np.ndarray, rotation: int) -> np.ndarray:
    if rotation == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    elif rotation == 270 or rotation == -90:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame

def extract_and_normalize_frame(cap: cv2.VideoCapture, rotation: int = 0, target_width: int = 640):
    """Reads a frame, applies rotation, and resizes for fast ML transmission."""
    ret, frame = cap.read()
    if not ret:
        return False, None
    
    # Apply rotation if present in metadata
    frame = apply_rotation(frame, rotation)
    
    # Calculate aspect ratio and resize (e.g. 4K portrait phone video is too massive)
    h, w = frame.shape[:2]
    if w > target_width:
        ratio = target_width / w
        new_h = int(h * ratio)
        frame = cv2.resize(frame, (target_width, new_h), interpolation=cv2.INTER_AREA)
        
    return True, frame
