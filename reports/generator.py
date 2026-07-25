"""Generates JSON, HTML, and PDF vulnerability reports from a scan result.

Expected scan result shape (see backend/services/pipeline.py, which builds this):

    {
        "scan_id": str,
        "created_at": "2026-07-25T12:00:00",
        "target": str,                     # file path or repo URL that was scanned
        "files": [
            {"file": str, "language": str, "tier": int, "layers_run": [str, ...], "findings": [...]},
        ],
        "summary": {"total_findings": int, "by_severity": {...}, "files_scanned": int},
    }
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

_SEVERITY_COLOR = {
    "critical": "#7f1d1d",
    "high": "#b91c1c",
    "medium": "#b45309",
    "low": "#15803d",
}


def to_json(scan_result: dict, indent: int = 2) -> str:
    return json.dumps(scan_result, indent=indent)


def to_html(scan_result: dict) -> str:
    summary = scan_result.get("summary", {})
    rows = []
    for file_entry in scan_result.get("files", []):
        for finding in file_entry.get("findings", []):
            color = _SEVERITY_COLOR.get(finding.get("severity", "medium"), "#374151")
            rows.append(
                f"""<tr>
                    <td>{escape(file_entry.get('file', ''))}:{finding.get('line', '?')}</td>
                    <td>{escape(str(finding.get('type', '')))}</td>
                    <td>{escape(str(finding.get('cwe') or '-'))}</td>
                    <td><span style="color:{color};font-weight:600">{escape(finding.get('severity', ''))}</span></td>
                    <td>{finding.get('confidence', 0):.2f}</td>
                    <td>{escape(', '.join(finding.get('sources', [])))}</td>
                    <td>{escape(str(finding.get('explanation', '')))}</td>
                    <td>{escape(str(finding.get('suggested_fix') or '-'))}</td>
                </tr>"""
            )

    rows_html = "\n".join(rows) if rows else "<tr><td colspan=\"8\">No findings.</td></tr>"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Vulnerability Report - {escape(scan_result.get('scan_id', ''))}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; margin: 2rem; color: #111827; }}
  h1 {{ font-size: 1.4rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ border: 1px solid #d1d5db; padding: 0.5rem; text-align: left; font-size: 0.85rem; vertical-align: top; }}
  th {{ background: #f3f4f6; }}
  .summary {{ display: flex; gap: 1.5rem; margin-top: 0.5rem; }}
  .summary div {{ background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 0.5rem 1rem; }}
</style>
</head>
<body>
  <h1>Vulnerability Scan Report</h1>
  <p><strong>Scan ID:</strong> {escape(scan_result.get('scan_id', ''))} &nbsp;
     <strong>Target:</strong> {escape(scan_result.get('target', ''))} &nbsp;
     <strong>Date:</strong> {escape(scan_result.get('created_at', ''))}</p>
  <div class="summary">
    <div><strong>Files scanned:</strong> {summary.get('files_scanned', 0)}</div>
    <div><strong>Total findings:</strong> {summary.get('total_findings', 0)}</div>
    <div><strong>Critical/High:</strong> {summary.get('by_severity', {}).get('critical', 0) + summary.get('by_severity', {}).get('high', 0)}</div>
  </div>
  <table>
    <thead>
      <tr><th>Location</th><th>Type</th><th>CWE</th><th>Severity</th><th>Confidence</th><th>Sources</th><th>Explanation</th><th>Suggested Fix</th></tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</body>
</html>"""


def to_pdf(scan_result: dict, output_path: str | Path) -> Path:
    """Renders the HTML report to PDF via WeasyPrint. Raises a clear error if it's not installed."""
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
            "PDF export requires WeasyPrint (`pip install -r requirements.txt`), which also needs "
            "its native Pango/Cairo dependencies installed on the host system."
        ) from exc

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=to_html(scan_result)).write_pdf(str(output_path))
    return output_path


def build_summary(files: list[dict]) -> dict:
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total = 0
    for file_entry in files:
        for finding in file_entry.get("findings", []):
            total += 1
            severity = finding.get("severity", "medium")
            by_severity[severity] = by_severity.get(severity, 0) + 1
    return {"total_findings": total, "by_severity": by_severity, "files_scanned": len(files)}
