"""GET /report/{scan_id}, GET /report/{scan_id}/pdf, GET /history."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.models.db import get_scan, list_scans
from backend.models.schemas import ScanHistoryEntry, ScanResult
from reports.generator import to_pdf

router = APIRouter(tags=["report"])


@router.get("/report/{scan_id}", response_model=ScanResult)
def get_report(scan_id: str) -> dict:
    result = get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No scan found with id {scan_id}")
    return result


@router.get("/report/{scan_id}/pdf")
def get_report_pdf(scan_id: str) -> FileResponse:
    result = get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No scan found with id {scan_id}")

    try:
        pdf_path = Path(tempfile.gettempdir()) / f"securify_report_{scan_id}.pdf"
        to_pdf(result, pdf_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    return FileResponse(pdf_path, media_type="application/pdf", filename=f"report_{scan_id}.pdf")


@router.get("/history", response_model=list[ScanHistoryEntry])
def get_history(limit: int = 50) -> list[dict]:
    return list_scans(limit=limit)
