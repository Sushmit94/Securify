"""FastAPI application entrypoint.

    uvicorn backend.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models.db import init_db
from backend.routes import report, scan

app = FastAPI(
    title="Securify - AI-Based Vulnerability Detection Framework",
    description="Hybrid static analysis + ML classifier + LLM reasoning source code scanner.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan.router)
app.include_router(report.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
