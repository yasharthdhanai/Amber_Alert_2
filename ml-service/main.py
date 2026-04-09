from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import base64
import numpy as np
import cv2
import insightface
from insightface.app import FaceAnalysis

app = FastAPI(title="Missing Child Finder - GPU ML Engine")

# NOTE: The InsightFace 'FaceAnalysis' pipeline natively uses RetinaFace for bounding box 
# detection and facial landmarking before passing it to ArcFace for recognition embeddings.
# We initialize it here prioritizing the GPU (CUDA).
print("Initializing RetinaFace & ArcFace Models via InsightFace...")
try:
    face_app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    face_app.prepare(ctx_id=0, det_size=(640, 640)) 
except Exception as e:
    print(f"Warning: InsightFace init failed (normal if running locally without models/GPU): {e}")

# ── Request Schemas ───────────────────────────────────────────────────
class ReferenceRequest(BaseModel):
    reference_image_b64: str

class AnalyzeRequest(BaseModel):
    frame_b64: str
    reference_embedding: list[float]  # 512-dim vector

# ── Endpoints ──────────────────────────────────────────────────────────
@app.get("/")
def health_check():
    return {"status": "ok", "gpu_enabled": True, "model": "buffalo_l"}

@app.post("/extract-reference")
def extract_reference(req: ReferenceRequest):
    """
    Receives a Base64-encoded reference photo of the missing child.
    Returns the 512-dimensional ArcFace embedding for future matching.
    """
    try:
        img_data = base64.b64decode(req.reference_image_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode the reference image.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")

    # RetinaFace detects faces
    faces = face_app.get(img)
    if not faces:
        raise HTTPException(status_code=400, detail="No face (RetinaFace) detected in reference photo. Please upload a clear frontal photo.")
    
    # ArcFace extracts the 512-dim embedding of the most prominent (largest) face
    largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    embedding = largest_face.embedding.tolist()
    bbox = largest_face.bbox.tolist()

    return {
        "embedding": embedding,
        "face_detected": True,
        "bbox": bbox,
        "embedding_dim": len(embedding)
    }

@app.post("/analyze")
def analyze_frame(req: AnalyzeRequest):
    """
    Receives a Base64-encoded CCTV frame + reference embedding.
    Returns all matching faces with confidence scores and bounding boxes.
    """
    try:
        img_data = base64.b64decode(req.frame_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"matches": [], "faces_detected": 0, "error": "Could not decode frame"}
    except Exception:
        return {"matches": [], "faces_detected": 0, "error": "Invalid frame data"}

    # RetinaFace detects all faces in the frame
    faces = face_app.get(img)
    ref_emb = np.array(req.reference_embedding, dtype=np.float32)

    matches = []
    for face in faces:
        # ArcFace Embedding Cosine Similarity Check
        sim = np.dot(face.embedding, ref_emb) / (np.linalg.norm(face.embedding) * np.linalg.norm(ref_emb))
        if sim > 0.68:  # Threshold for positive match
            matches.append({
                "confidence": round(float(sim), 4),
                "bbox": [round(c, 1) for c in face.bbox.tolist()]
            })

    # Sort matches by confidence descending
    matches.sort(key=lambda m: m["confidence"], reverse=True)

    return {
        "matches": matches,
        "faces_detected": len(faces),
        "faces_matched": len(matches)
    }
