import { useState } from "react";
import FindingsTable from "../components/FindingsTable.jsx";

export default function Dashboard() {
  const [file, setFile] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

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

  return (
    <div>
      <h1>Securify - Vulnerability Scanner</h1>
      <p>Upload a source file to run it through the static analysis, ML classifier, and LLM reasoning layers.</p>

      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={handleScan} disabled={!file || scanning} style={{ marginLeft: "0.5rem" }}>
        {scanning ? "Scanning..." : "Scan"}
      </button>

      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}

      {result && (
        <>
          <div className="summary">
            <div><strong>Files scanned:</strong> {result.summary.files_scanned}</div>
            <div><strong>Total findings:</strong> {result.summary.total_findings}</div>
            <div><strong>Scan ID:</strong> {result.scan_id}</div>
          </div>
          <FindingsTable files={result.files} />
        </>
      )}
    </div>
  );
}
