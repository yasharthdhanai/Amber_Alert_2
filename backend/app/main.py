from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routers import cases
from .database import init_db
import os

app = FastAPI(title="Missing Child Finder API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_db()
    # Ensure storage directories exist
    storage_dir = os.path.join(os.path.dirname(__file__), "..", "storage")
    for subdir in ["photos", "videos", "screenshots"]:
        os.makedirs(os.path.join(storage_dir, subdir), exist_ok=True)

app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])

@app.get("/")
def root():
    return {"status": "ok", "message": "Missing Child Finder API running."}

@app.get("/api/health")
def health():
    ml_url = os.environ.get("ML_SERVICE_URL", "http://localhost:8050")
    return {
        "status": "ok",
        "ml_service_url": ml_url,
        "version": "1.0.0"
    }
