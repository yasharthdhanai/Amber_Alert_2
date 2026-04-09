from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import cases
from .database import init_db

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

app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])

@app.get("/")
def root():
    return {"status": "ok", "message": "Missing Child Finder API running."}
