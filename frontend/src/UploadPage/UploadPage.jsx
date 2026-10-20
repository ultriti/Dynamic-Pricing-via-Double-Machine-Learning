import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchDatasetPreview, fetchDatasetSummary, getApiErrorMessage, uploadDataset } from "../services/api";
import "./UploadPage.css";

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

const UploadPage = () => {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null);
  const [summary, setSummary] = useState(null);
  const navigate = useNavigate();

  const selectFile = (selected) => {
    if (!selected) return;
    setResult(null);
    setPreview(null);
    setSummary(null);
    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setFile(null);
      setError("Only CSV files are accepted.");
      return;
    }
    if (selected.size > MAX_UPLOAD_BYTES) {
      setFile(null);
      setError("File is too large. Maximum upload size is 20 MB.");
      return;
    }
    setFile(selected);
    setError(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    selectFile(e.dataTransfer.files[0]);
  };

  const handleFileSelect = (e) => {
    selectFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await uploadDataset(file);

      setResult(data);
      if (!data.hillstrom_compatibility?.compatible_columns) {
        return;
      }
      const [datasetPreview, datasetSummary] = await Promise.all([
        fetchDatasetPreview(),
        fetchDatasetSummary(),
      ]);
      setPreview(datasetPreview);
      setSummary(datasetSummary);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page upload">
      <div className="page-heading">
        <div>
          <h1>Upload Dataset</h1>
          <p>Upload a Hillstrom CSV file to begin analysis.</p>
        </div>
      </div>

      <div
        className={`dropzone ${dragging ? "drag-over" : ""} ${file ? "has-file" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={(event) => {
          if (event.target.id !== "csv-input") {
            document.getElementById("csv-input").click();
          }
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            document.getElementById("csv-input").click();
          }
        }}
      >
        <input
          id="csv-input"
          type="file"
          accept=".csv"
          onChange={handleFileSelect}
          hidden
        />
        {file ? (
          <div className="file-selected">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <div>
              <span className="file-name">{file.name}</span>
              <span className="file-meta">{(file.size / 1024).toFixed(1)} KB</span>
            </div>
          </div>
        ) : (
          <>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <p className="drop-label">Drop your CSV file here, or <span>browse</span></p>
          </>
        )}
      </div>

      {error && <div className="msg msg-error">{error}</div>}

      <div className="actions">
        <button className="btn-primary" onClick={handleUpload} disabled={!file || loading}>
          {loading ? "Uploading…" : "Upload"}
        </button>
      </div>

      {result && (
        <div className="result-section">
          <div className="msg msg-success">
            Dataset <strong>{result.filename}</strong> uploaded — {result.rows?.toLocaleString()} rows, {result.columns?.length} columns, {result.missing_values} missing values.
          </div>

          {!result.hillstrom_compatibility?.compatible_columns && (
            <div className="msg msg-error" role="alert">
              {result.hillstrom_compatibility?.message ?? "This dataset is not compatible with the Hillstrom analysis."}
              {result.hillstrom_compatibility?.missing_columns?.length > 0 && (
                <> Missing columns: {result.hillstrom_compatibility.missing_columns.join(", ")}.</>
              )}
            </div>
          )}

          <div className="meta-row">
            {result.columns?.map((col) => (
              <span key={col} className="tag">{col}</span>
            ))}
          </div>

          {preview?.data && (
            <div className="table-card">
              <div className="table-card-header">Preview</div>
              <div className="table-scroll">
                <table className="tbl">
                  <thead>
                    <tr>{preview.columns.map((c) => <th key={c}>{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {preview.data.map((row, i) => (
                      <tr key={i}>{preview.columns.map((c) => <td key={c}>{row[c]}</td>)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {summary && (
            <p className="upload-summary">
              Conversion rate: {summary.conversion_rate_percent ?? "—"}% · Visit rate: {summary.visit_rate_percent ?? "—"}%
            </p>
          )}

          {result.hillstrom_compatibility?.compatible_columns && (
            <div className="actions">
              <button className="btn-primary" onClick={() => navigate("/")}>Go to dashboard</button>
              <button className="btn-secondary" onClick={() => navigate("/eda")}>Explore dataset</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default UploadPage;
