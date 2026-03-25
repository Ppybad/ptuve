from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.database import init_db
from backend.app.api.endpoints import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "https://d2ba-189-240-208-186.ngrok-free.app",
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

app.include_router(router, prefix="/api/v1")
