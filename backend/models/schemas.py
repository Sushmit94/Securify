"""Pydantic request/response models for the REST API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Finding(BaseModel):
    line: int
    end_line: int
    type: str
    cwe: str | None = None
    severity: str
    confidence: float
    sources: list[str]
    rule_id: str | None = None
    function_name: str | None = None
    explanation: str
    suggested_fix: str | None = None
    file: str


class FileResult(BaseModel):
    file: str
    language: str | None
    tier: int
    layers_run: list[str]
    findings: list[Finding]


class ScanSummary(BaseModel):
    total_findings: int
    by_severity: dict[str, int]
    files_scanned: int


class ScanResult(BaseModel):
    scan_id: str
    created_at: str
    target: str
    files: list[FileResult]
    summary: ScanSummary


class RepoScanRequest(BaseModel):
    repo_url: str = Field(..., description="URL of a public GitHub repository to clone and scan.")
    max_files: int = Field(200, ge=1, le=2000)


class ScanHistoryEntry(BaseModel):
    scan_id: str
    target: str
    created_at: str
    total_findings: int
