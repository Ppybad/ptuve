from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/downloads_dir")
def downloads_dir():
    return {"downloads_dir": os.environ.get("DOWNLOADS_DIR", "/downloads")}
