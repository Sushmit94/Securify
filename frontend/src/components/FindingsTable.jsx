export default function FindingsTable({ files }) {
  const rows = files.flatMap((f) =>
    f.findings.map((finding) => ({ file: f.file, ...finding }))
  );

  if (rows.length === 0) {
    return <p>No findings.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Location</th>
          <th>Type</th>
          <th>CWE</th>
          <th>Severity</th>
          <th>Confidence</th>
          <th>Sources</th>
          <th>Explanation</th>
          <th>Suggested Fix</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td>{r.file}:{r.line}</td>
            <td>{r.type}</td>
            <td>{r.cwe || "-"}</td>
            <td className={`severity-${r.severity}`}>{r.severity}</td>
            <td>{r.confidence?.toFixed(2)}</td>
            <td>{r.sources?.join(", ")}</td>
            <td>{r.explanation}</td>
            <td>{r.suggested_fix || "-"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
