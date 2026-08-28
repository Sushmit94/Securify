import { useState, useEffect, useRef, useCallback } from "react";
import FindingsTable from "../components/FindingsTable.jsx";
import "./Dashboard.css";

const PIPELINE_STAGES = [
  { key: "static", label: "Static Analysis", icon: "🔍" },
  { key: "ml", label: "ML Classifier", icon: "🧠" },
  { key: "llm", label: "LLM Reasoning", icon: "⚡" },
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
    if (!file) return;
    setScanning(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/scan/file", { method: "POST", body: formData });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Scan failed (${res.status})`);
      }
      setResult(await res.json());
    } catch (err) {
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

  return (
    <div className="dash-shell">
      {/* Animated Background */}
      <div className="dash-bg">
        <div className="dash-bg-orb" />
        <div className="dash-bg-orb" />
        <div className="dash-bg-orb" />
      </div>

      {/* Mobile header */}
      <div className="dash-mobile-header">
        <div className="dash-mobile-brand">
          <div className="dash-mobile-logo">S</div>
          Securify
        </div>
        <button
          className="dash-hamburger"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Toggle menu"
        >
          {sidebarOpen ? "✕" : "☰"}
        </button>
      </div>

      {/* Mobile overlay */}
      <div
        className={`dash-overlay ${sidebarOpen ? "is-visible" : ""}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside className={`dash-sidebar ${sidebarOpen ? "is-open" : ""}`}>
        <div className="dash-sidebar-brand">
          <div className="dash-sidebar-logo">
            <div className="dash-logo-icon">S</div>
            <span className="dash-logo-text">Securify</span>
            <span className="dash-logo-badge">v1</span>
          </div>
        </div>

        <nav className="dash-sidebar-nav">
          <button className="dash-nav-item is-active">
            <span className="dash-nav-icon">🛡️</span>
            Scanner
          </button>
          <button className="dash-nav-item" disabled>
            <span className="dash-nav-icon">📊</span>
            Analytics
          </button>
          <button className="dash-nav-item" disabled>
            <span className="dash-nav-icon">⚙️</span>
            Settings
          </button>
        </nav>

        <div className="dash-sidebar-section">
          <div className="dash-sidebar-section-title">Recent Scans</div>
          {history.length === 0 ? (
            <div className="dash-history-empty">No scans yet</div>
          ) : (
            history.map((h) => (
              <button
                key={h.scan_id}
                className="dash-history-item"
                onClick={() => loadHistoryScan(h.scan_id)}
              >
                <span className="dash-history-target">{h.target}</span>
                <span className="dash-history-meta">
                  <span className="dash-history-findings-count">
                    {h.total_findings} findings
                  </span>
                  <span>·</span>
                  <span>{formatDate(h.created_at)}</span>
                </span>
              </button>
            ))
          )}
        </div>

        <div className="dash-sidebar-footer">
          <div className="dash-sidebar-status">
            <span
              className={`dash-status-dot ${scanning ? "is-scanning" : ""}`}
            />
            {scanning ? "Scanning…" : "System Ready"}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="dash-main">
        <div className="dash-page-header">
          <h1>Vulnerability Scanner</h1>
          <p className="dash-page-subtitle">
            Upload a file to scan for security vulnerabilities using static
            analysis, ML classification, and LLM reasoning.
          </p>
        </div>

        {/* Upload Zone */}
        {!scanning && (
          <div
            className={`dash-upload-zone ${dragover ? "is-dragover" : ""} ${
              file ? "has-file" : ""
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => !file && fileInputRef.current?.click()}
          >
            {file ? (
              <>
                <div className="dash-file-preview">
                  <div className="dash-file-icon">📄</div>
                  <div className="dash-file-info">
                    <div className="dash-file-name">{file.name}</div>
                    <div className="dash-file-size">
                      {formatBytes(file.size)}
                    </div>
                  </div>
                  <button
                    className="dash-file-remove"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                    title="Remove file"
                  >
                    ✕
                  </button>
                </div>
                <div className="dash-upload-actions">
                  <label className="dash-btn dash-btn-ghost">
                    Change file
                    <input
                      ref={fileInputRef}
                      type="file"
                      onChange={(e) => setFile(e.target.files[0])}
                      hidden
                    />
                  </label>
                  <button
                    className="dash-btn dash-btn-primary"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleScan();
                    }}
                    disabled={!file || scanning}
                  >
                    🚀 Run Scan
                  </button>
                </div>
              </>
            ) : (
              <>
                <span className="dash-upload-icon">🔒</span>
                <div className="dash-upload-title">
                  Drop your file here to scan
                </div>
                <div className="dash-upload-subtitle">
                  or click to browse — supports source code files in all major
                  languages
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

        {/* Scanning Progress */}
        {scanning && (
          <div className="dash-scanning">
            <div className="dash-scanning-header">
              <div className="dash-scanning-spinner" />
              <span className="dash-scanning-title">
                Analyzing vulnerabilities…
              </span>
              {file && (
                <span className="dash-scanning-file">{file.name}</span>
              )}
            </div>

            <div className="dash-pipeline">
              {PIPELINE_STAGES.map((stage, i) => (
                <div
                  key={stage.key}
                  className={`dash-pipeline-stage ${
                    i < pipelineStage
                      ? "is-done"
                      : i === pipelineStage
                      ? "is-active"
                      : ""
                  }`}
                >
                  <div className="dash-pipeline-dot">
                    {i < pipelineStage ? "✓" : stage.icon}
                  </div>
                  <span className="dash-pipeline-label">{stage.label}</span>
                  <div className="dash-pipeline-connector" />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="dash-error">
            <span className="dash-error-icon">⚠️</span>
            <div className="dash-error-content">
              <div className="dash-error-label">Scan Failed</div>
              <div className="dash-error-msg">{error}</div>
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="dash-results">
            <div className="dash-results-header">
              <span className="dash-results-title">Scan Results</span>
              <div className="dash-results-actions">
                <button
                  className="dash-btn dash-btn-outline"
                  onClick={handleDownloadPDF}
                >
                  📄 Download PDF
                </button>
                <button
                  className="dash-btn dash-btn-primary"
                  onClick={() => {
                    setResult(null);
                    setFile(null);
                  }}
                >
                  + New Scan
                </button>
              </div>
            </div>

            {/* Scan ID */}
            <div className="dash-scan-id-row">
              <span className="dash-scan-id-label">Scan ID</span>
              <span className="dash-scan-id-value">{result.scan_id}</span>
              <button
                className="dash-scan-id-copy"
                onClick={handleCopyId}
                title="Copy scan ID"
              >
                {copiedId ? "✓" : "📋"}
              </button>
            </div>

            {/* Stat Cards */}
            <div className="dash-stats-grid">
              <div className="dash-stat-card">
                <div className="dash-stat-label">Files Scanned</div>
                <div className="dash-stat-value">
                  {result.summary.files_scanned}
                </div>
              </div>
              <div className="dash-stat-card">
                <div className="dash-stat-label">Total Findings</div>
                <div className="dash-stat-value">
                  {result.summary.total_findings}
                </div>
              </div>
              <div className="dash-stat-card">
                <div className="dash-stat-label">Critical / High</div>
                <div className="dash-stat-value">
                  {(severities.critical || 0) + (severities.high || 0)}
                </div>
              </div>
              <div className="dash-stat-card">
                <div className="dash-stat-label">Scanned At</div>
                <div className="dash-stat-value is-mono-sm">
                  {formatDate(result.created_at)}
                </div>
              </div>
            </div>

            {/* Severity Breakdown */}
            {result.summary.total_findings > 0 && (
              <>
                <div className="dash-section-title">Severity Breakdown</div>
                <div className="dash-severity-row">
                  {["critical", "high", "medium", "low"].map(
                    (sev) =>
                      (severities[sev] || 0) > 0 && (
                        <div key={sev} className="dash-severity-chip">
                          <span
                            className={`dash-severity-dot ${sev}`}
                          />
                          <span className="dash-severity-chip-label">
                            {sev.charAt(0).toUpperCase() + sev.slice(1)}
                          </span>
                          <span className="dash-severity-chip-count">
                            {severities[sev]}
                          </span>
                        </div>
                      )
                  )}
                </div>
              </>
            )}

            {/* Findings Table */}
            <div className="dash-section-title">Findings Detail</div>
            <FindingsTable files={result.files} />
          </div>
        )}
      </main>
    </div>
  );
}