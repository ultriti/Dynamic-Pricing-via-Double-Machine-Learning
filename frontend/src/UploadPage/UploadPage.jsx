import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./UploadPage.css";

const API = "http://localhost:8000";

const UploadPage = () => {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null);
  const navigate = useNavigate();

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && dropped.name.endsWith(".csv")) {
      setFile(dropped);
      setError(null);
    } else {
      setError("Only CSV files are accepted.");
    }
  };

  const handleFileSelect = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API}/api/dataset/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");

      setResult(data);

      const prevRes = await fetch(`${API}/api/dataset/preview`);
      if (prevRes.ok) setPreview(await prevRes.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload">
      <h1 className="page-title">Upload dataset</h1>
      <p className="page-desc">Upload a CSV file to begin analysis</p>

      <div
        className={`dropzone ${dragging ? "drag-over" : ""} ${file ? "has-file" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById("csv-input").click()}
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
          <div className="msg msg-success">Dataset uploaded — {result.rows?.toLocaleString()} rows, {result.columns?.length} columns, {result.missing_values} missing values.</div>

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

          <div className="actions">
            <button className="btn-primary" onClick={() => navigate("/eda")}>Continue to analysis</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default UploadPage;
