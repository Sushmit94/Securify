import { useState } from "react";
import "./FindingsTable.css";

function getConfidenceLevel(val) {
  if (val >= 0.8) return "high";
  if (val >= 0.5) return "mid";
  return "low";
}

function getSourceClass(source) {
  const s = source.toLowerCase().replace(/[\s-]/g, "_");
  if (s.includes("static")) return "static_analysis";
  if (s.includes("ml")) return "ml_classifier";
  if (s.includes("llm")) return "llm";
  return "generic";
}

export default function FindingsTable({ files }) {
  const [expandedRow, setExpandedRow] = useState(null);

  const rows = files.flatMap((f) =>
    f.findings.map((finding) => ({ file: f.file, ...finding }))
  );

  if (rows.length === 0) {
    return (
      <div className="findings-table-wrap">
        <div className="findings-empty">
          <span className="findings-empty-icon">🎉</span>
          <div className="findings-empty-title">No vulnerabilities found</div>
          <div className="findings-empty-subtitle">
            This file passed all security checks
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="findings-table-wrap">
      <table className="findings-table">
        <thead>
          <tr>
            <th style={{ width: 28 }}></th>
            <th>Location</th>
            <th>Type</th>
            <th>CWE</th>
            <th>Severity</th>
            <th>Confidence</th>
            <th>Sources</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const isOpen = expandedRow === i;
            return (
              <>
                <tr
                  key={`row-${i}`}
                  onClick={() => setExpandedRow(isOpen ? null : i)}
                >
                  <td>
                    <span
                      className={`findings-chevron ${isOpen ? "is-open" : ""}`}
                    >
                      ▶
                    </span>
                  </td>
                  <td>
                    <span className="findings-location">
                      {r.file}
                      <span className="findings-location-line">:{r.line}</span>
                    </span>
                  </td>
                  <td>
                    <span className="findings-type">{r.type}</span>
                  </td>
                  <td>
                    <span
                      className={`findings-cwe ${!r.cwe ? "is-none" : ""}`}
                    >
                      {r.cwe || "—"}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`findings-severity-badge ${r.severity?.toLowerCase()}`}
                    >
                      {r.severity}
                    </span>
                  </td>
                  <td>
                    <div className="findings-confidence">
                      <div className="findings-confidence-bar">
                        <div
                          className={`findings-confidence-fill ${getConfidenceLevel(
                            r.confidence
                          )}`}
                          style={{
                            width: `${(r.confidence * 100).toFixed(0)}%`,
                          }}
                        />
                      </div>
                      <span className="findings-confidence-label">
                        {(r.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="findings-sources">
                      {r.sources?.map((s, si) => (
                        <span
                          key={si}
                          className={`findings-source-pill ${getSourceClass(s)}`}
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
                {isOpen && (
                  <tr key={`expand-${i}`} className="findings-expand-row">
                    <td colSpan={7}>
                      <div className="findings-expand-content">
                        <div className="findings-expand-grid">
                          <div className="findings-expand-block">
                            <span className="findings-expand-label">
                              Explanation
                            </span>
                            <p className="findings-expand-text">
                              {r.explanation}
                            </p>
                          </div>
                          <div className="findings-expand-block">
                            <span className="findings-expand-label">
                              Suggested Fix
                            </span>
                            <p className="findings-expand-text is-fix">
                              {r.suggested_fix || "No fix suggestion available"}
                            </p>
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
