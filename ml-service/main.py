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

# (In a real deployment, SAM 3.1 / SAM 2 would be initialized here via meta's repo.)
# sam_predictor = SAM2ImagePredictor(build_sam2(..))

class ReferenceRequest(BaseModel):
    reference_image_b64: str

class AnalyzeRequest(BaseModel):
    frame_b64: str
    reference_embedding: list[float]  # 512-dim vector

@app.get("/")
def health_check():
    return {"status": "ok", "gpu_enabled": True}

@app.post("/extract-reference")
def extract_reference(req: ReferenceRequest):
    img_data = base64.b64decode(req.reference_image_b64)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # RetinaFace detects faces
    faces = face_app.get(img)
    if not faces:
        raise HTTPException(status_code=400, detail="No face (RetinaFace) detected in reference photo")
    
    # ArcFace extracts the 512-dim embedding of the most prominent face
    embedding = faces[0].embedding.tolist()
    return {"embedding": embedding}

@app.post("/analyze")
def analyze_frame(req: AnalyzeRequest):
    img_data = base64.b64decode(req.frame_b64)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # RetinaFace detects all faces in the frame
    faces = face_app.get(img)
    ref_emb = np.array(req.reference_embedding, dtype=np.float32)

    matches = []
    for face in faces:
        # ArcFace Embedding Cosine Similarity Check
        sim = np.dot(face.embedding, ref_emb) / (np.linalg.norm(face.embedding) * np.linalg.norm(ref_emb))
        if sim > 0.68:  # Threshold for positive match
            bbox = face.bbox.tolist()
            
            # --- SAM 3.1 (Segment Anything) ---
            # predictor.set_image(img)
            # masks, scores, _ = predictor.predict(box=face.bbox)
            # pseudo-mask for scaffold:
            
            matches.append({
                "confidence": float(sim),
                "bbox": bbox
            })
            
    return {"matches": matches}
