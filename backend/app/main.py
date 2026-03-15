from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .api.endpoints import query, catalog, upload

app = FastAPI(title="PondHouse Data Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["catalog"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "PondHouse Control Plane"}

# Serve the React frontend (the single pane of glass)
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
