import { useState, useEffect, useRef, useCallback } from "react";
import FindingsTable from "../components/FindingsTable.jsx";
import "./Dashboard.css";

const PIPELINE_STAGES = [
  { key: "static", label: "Static analysis", detail: "Semgrep + Bandit rulesets" },
  { key: "ml", label: "ML classifier", detail: "Fine-tuned CodeBERT" },
  { key: "llm", label: "LLM reasoning", detail: "Explains and filters findings" },
];

function formatBytes(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

export default function Dashboard() {
  const [file, setFile] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragover, setDragover] = useState(false);
  const [pipelineStage, setPipelineStage] = useState(0);
  const [history, setHistory] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [copiedId, setCopiedId] = useState(false);
  const fileInputRef = useRef(null);
  const pipelineTimer = useRef(null);

  // Fetch scan history
  useEffect(() => {
    fetch("/history?limit=20")
      .then((r) => (r.ok ? r.json() : []))
      .then(setHistory)
      .catch(() => {});
  }, [result]);

  // Pipeline stage animation
  useEffect(() => {
    if (scanning) {
      setPipelineStage(0);
      let stage = 0;
      pipelineTimer.current = setInterval(() => {
        stage++;
        if (stage < PIPELINE_STAGES.length) {
          setPipelineStage(stage);
        }
      }, 2200);
    } else {
      clearInterval(pipelineTimer.current);
    }
    return () => clearInterval(pipelineTimer.current);
  }, [scanning]);

  async function handleScan() {
    console.log("handleScan fired, file =", file);
    if (!file) {
      console.warn("handleScan: no file selected, returning early");
      return;
    }
    setScanning(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    console.log("handleScan: sending POST /scan/file for", file.name, file.size, "bytes");
    try {
      const res = await fetch("/scan/file", { method: "POST", body: formData });
      console.log("handleScan: response status", res.status);
      const text = await res.text();
      console.log("handleScan: response body (first 500 chars)", text.substring(0, 500));
      if (!res.ok) {
        let detail = `Scan failed (${res.status})`;
        try {
          detail = JSON.parse(text).detail || detail;
        } catch {}
        throw new Error(detail);
      }
      const data = JSON.parse(text);
      console.log("handleScan: parsed result, scan_id =", data.scan_id);
      setResult(data);
    } catch (err) {
      console.error("handleScan: error", err);
      setError(err.message);
    } finally {
      setScanning(false);
    }
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragover(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  }, []);

  function handleDragOver(e) {
    e.preventDefault();
    setDragover(true);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    setDragover(false);
  }

  async function handleDownloadPDF() {
    if (!result?.scan_id) return;
    try {
      const res = await fetch(`/report/${result.scan_id}/pdf`);
      if (!res.ok) throw new Error("PDF generation failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${result.scan_id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* silently fail */
    }
  }

  function handleCopyId() {
    if (!result?.scan_id) return;
    navigator.clipboard.writeText(result.scan_id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  }

  async function loadHistoryScan(scanId) {
    try {
      const res = await fetch(`/report/${scanId}`);
      if (!res.ok) return;
      setResult(await res.json());
      setError(null);
      setFile(null);
      setSidebarOpen(false);
    } catch {
      /* silently fail */
    }
  }

  const severities = result?.summary?.by_severity || {};
  const severityOrder = ["critical", "high", "medium", "low"];

  return (
    <div className="sc-shell">
      {/* Mobile top bar */}
      <div className="sc-topbar">
        <div className="sc-brand">
          <span className="sc-brand-mark">S</span>
          <span className="sc-brand-name">Securify</span>
        </div>
        <button
          className="sc-menu-btn"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Toggle menu"
        >
          {sidebarOpen ? "✕" : "☰"}
        </button>
      </div>

      <div
        className={`sc-scrim ${sidebarOpen ? "is-visible" : ""}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Rail */}
      <aside className={`sc-rail ${sidebarOpen ? "is-open" : ""}`}>
        <div className="sc-rail-brand">
          <span className="sc-brand-mark">S</span>
          <div className="sc-rail-brand-text">
            <span className="sc-rail-brand-name">Securify</span>
            <span className="sc-rail-brand-tag">vulnerability scanner</span>
          </div>
        </div>

        <nav className="sc-rail-nav">
          <button className="sc-rail-item is-active">Scanner</button>
          <button className="sc-rail-item" disabled>
            Analytics
          </button>
          <button className="sc-rail-item" disabled>
            Settings
          </button>
        </nav>

        <div className="sc-rail-section">
          <div className="sc-rail-label">Recent scans</div>
          {history.length === 0 ? (
            <div className="sc-rail-empty">Nothing scanned yet</div>
          ) : (
            <div className="sc-rail-list">
              {history.map((h) => (
                <button
                  key={h.scan_id}
                  className="sc-history-row"
                  onClick={() => loadHistoryScan(h.scan_id)}
                >
                  <span className="sc-history-name">{h.target}</span>
                  <span className="sc-history-meta">
                    <span>{h.total_findings} findings</span>
                    <span>{formatDate(h.created_at)}</span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="sc-rail-status">
          <span className={`sc-status-dot ${scanning ? "is-active" : ""}`} />
          {scanning ? "Scanning" : "Ready"}
        </div>
      </aside>

      {/* Main */}
      <main className="sc-main">
        <header className="sc-header">
          <h1>Scan a file for vulnerabilities</h1>
          <p>
            Runs static analysis, a fine-tuned ML classifier, and LLM
            reasoning, then merges what each layer finds into one report.
          </p>
        </header>

        {!scanning && !result && (
          <div
            className={`sc-intake ${dragover ? "is-dragover" : ""} ${
              file ? "has-file" : ""
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => !file && fileInputRef.current?.click()}
          >
            {file ? (
              <>
                <div className="sc-intake-file">
                  <div className="sc-intake-file-main">
                    <span className="sc-intake-file-name">{file.name}</span>
                    <span className="sc-intake-file-size">
                      {formatBytes(file.size)}
                    </span>
                  </div>
                  <button
                    className="sc-icon-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                    title="Remove file"
                  >
                    ✕
                  </button>
                </div>
                <div className="sc-intake-actions">
                  <label className="sc-btn sc-btn-ghost">
                    Change file
                    <input
                      ref={fileInputRef}
                      type="file"
                      onChange={(e) => setFile(e.target.files[0])}
                      hidden
                    />
                  </label>
                  <button
                    type="button"
                    className="sc-btn sc-btn-signal"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleScan();
                    }}
                    disabled={!file || scanning}
                  >
                    Run scan
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="sc-intake-title">
                  Drop a source file here, or click to browse
                </div>
                <div className="sc-intake-subtitle">
                  Any language is accepted — coverage depth depends on
                  language tier
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={(e) => setFile(e.target.files[0])}
                  hidden
                />
              </>
            )}
          </div>
        )}

        {scanning && (
          <div className="sc-log">
            <div className="sc-log-head">
              <span className="sc-log-title">Analyzing</span>
              {file && <span className="sc-log-file">{file.name}</span>}
            </div>
            <ol className="sc-log-stages">
              {PIPELINE_STAGES.map((stage, i) => (
                <li
                  key={stage.key}
                  className={`sc-log-stage ${
                    i < pipelineStage
                      ? "is-done"
                      : i === pipelineStage
                      ? "is-active"
                      : "is-pending"
                  }`}
                >
                  <span className="sc-log-marker">
                    {i < pipelineStage ? "✓" : i + 1}
                  </span>
                  <span className="sc-log-text">
                    <span className="sc-log-label">{stage.label}</span>
                    <span className="sc-log-detail">{stage.detail}</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {error && (
          <div className="sc-alert">
            <span className="sc-alert-label">Scan failed</span>
            <span className="sc-alert-msg">{error}</span>
          </div>
        )}

        {result && (
          <div className="sc-report">
            <div className="sc-report-head">
              <div>
                <span className="sc-report-title">Scan report</span>
                <div className="sc-report-id">
                  {result.scan_id}
                  <button
                    className="sc-copy-btn"
                    onClick={handleCopyId}
                    title="Copy scan ID"
                  >
                    {copiedId ? "copied" : "copy"}
                  </button>
                </div>
              </div>
              <div className="sc-report-actions">
                <button className="sc-btn sc-btn-ghost" onClick={handleDownloadPDF}>
                  Download PDF
                </button>
                <button
                  className="sc-btn sc-btn-signal"
                  onClick={() => {
                    setResult(null);
                    setFile(null);
                  }}
                >
                  New scan
                </button>
              </div>
            </div>

            <div className="sc-meta-row">
              <div className="sc-meta-item">
                <span className="sc-meta-label">Files scanned</span>
                <span className="sc-meta-value">
                  {result.summary.files_scanned}
                </span>
              </div>
              <div className="sc-meta-item">
                <span className="sc-meta-label">Total findings</span>
                <span className="sc-meta-value">
                  {result.summary.total_findings}
                </span>
              </div>
              <div className="sc-meta-item">
                <span className="sc-meta-label">Scanned</span>
                <span className="sc-meta-value sc-mono-sm">
                  {formatDate(result.created_at)}
                </span>
              </div>
            </div>

            {result.summary.total_findings > 0 && (
              <div className="sc-severity-row">
                {severityOrder.map(
                  (sev) =>
                    (severities[sev] || 0) > 0 && (
                      <div key={sev} className="sc-severity-item">
                        <span className={`sc-sev-dot sev-${sev}`} />
                        <span className="sc-sev-label">{sev}</span>
                        <span className="sc-sev-count">{severities[sev]}</span>
                      </div>
                    )
                )}
              </div>
            )}

            <div className="sc-report-section">
              <div className="sc-section-title">Findings</div>
              <FindingsTable files={result.files} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}