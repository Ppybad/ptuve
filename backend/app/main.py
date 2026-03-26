from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.database import init_db
from backend.app.api.endpoints import router
from backend.app.core.tidal_auth import ensure_session_and_start_device_login_if_needed
from backend.app.api.endpoints.tidal import router as tidal_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
def on_startup():
    init_db()
    ensure_session_and_start_device_login_if_needed()

app.include_router(router, prefix="/api/v1")
app.include_router(tidal_router, prefix="/api/v1")
