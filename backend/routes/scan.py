"""POST /scan/file and POST /scan/repo -- kick off a scan and return the result.

Both endpoints run the pipeline synchronously and return the full result once
done. For large repos this can take a while (each LLM call is a network round
trip); a background-job + polling design is a natural next step but is out of
scope for the current CLI/API-first pass (see README's Limitations & Future
Work).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from backend.models.db import save_scan
from backend.models.schemas import RepoScanRequest, ScanResult
from backend.services.pipeline import scan_paths, scan_repo

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/file", response_model=ScanResult)
async def scan_file_endpoint(file: UploadFile) -> dict:
    suffix = Path(file.filename or "upload").suffix
    contents = await file.read()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = scan_paths([tmp_path], target_label=file.filename or tmp_path)
        for file_entry in result["files"]:
            file_entry["file"] = file.filename or file_entry["file"]
            for finding in file_entry["findings"]:
                finding["file"] = file_entry["file"]
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    save_scan(result)
    return result


@router.post("/repo", response_model=ScanResult)
async def scan_repo_endpoint(request: RepoScanRequest) -> dict:
    try:
        result = scan_repo(request.repo_url, max_files=request.max_files)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    save_scan(result)
    return result
