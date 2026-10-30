import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  fetchDatasetList,
  fetchDatasetPreview,
  fetchDatasetSummary,
  getActiveDatasetId,
  getApiErrorMessage,
  setActiveDatasetId,
  uploadDataset,
} from "../services/api";
import "./UploadPage.css";

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
const CAMPAIGN_BUDGET_KEY = "econocausal:campaignBudget";
const REQUIRED_DATASET_FEATURES = [
  "recency",
  "history_segment",
  "history",
  "mens",
  "womens",
  "zip_code",
  "newbie",
  "channel",
];

const UploadPage = () => {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null);
  const [summary, setSummary] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [datasetListLoading, setDatasetListLoading] = useState(true);
  const [datasetListError, setDatasetListError] = useState(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState(
    () => getActiveDatasetId() ?? "",
  );
  const [campaignBudget, setCampaignBudget] = useState(() => {
    const savedBudget = Number(window.localStorage.getItem(CAMPAIGN_BUDGET_KEY));
    return Number.isFinite(savedBudget) && savedBudget >= 1 ? savedBudget : 5000;
  });
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    fetchDatasetList()
      .then(({ datasets: availableDatasets }) => {
        if (active) {
          setDatasets(availableDatasets);
          setDatasetListError(null);
        }
      })
      .catch((requestError) => {
        if (active) setDatasetListError(getApiErrorMessage(requestError));
      })
      .finally(() => {
        if (active) setDatasetListLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

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

  const handleBudgetChange = (event) => {
    const value = event.target.value;
    setCampaignBudget(value);
    const amount = Number(value);
    if (value !== "" && Number.isFinite(amount) && amount >= 1) {
      window.localStorage.setItem(CAMPAIGN_BUDGET_KEY, String(amount));
    } else {
      window.localStorage.removeItem(CAMPAIGN_BUDGET_KEY);
    }
  };
  const budgetIsValid =
    campaignBudget !== "" && Number.isFinite(Number(campaignBudget)) && Number(campaignBudget) >= 1;

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await uploadDataset(file);

      setResult(data);
      setSelectedDatasetId(data.dataset_id);
      fetchDatasetList()
        .then(({ datasets: availableDatasets }) => {
          setDatasets(availableDatasets);
          setDatasetListError(null);
        })
        .catch((requestError) =>
          setDatasetListError(getApiErrorMessage(requestError)),
        );
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
          <p>Upload historical campaign data and set the budget constraint for your analysis.</p>
        </div>
      </div>

      <section className="campaign-budget">
        <div>
          <label htmlFor="campaign-budget">Campaign budget (USD)</label>
          <p>Saved for the Week 3 allocation workflow; no discounts are allocated in this phase.</p>
        </div>
        <div className="budget-input-wrap">
          <span aria-hidden="true">$</span>
          <input
            id="campaign-budget"
            type="number"
            min="1"
            step="100"
            required
            value={campaignBudget}
            onChange={handleBudgetChange}
            aria-describedby="campaign-budget-help"
          />
        </div>
        <span id="campaign-budget-help" className="budget-saved">
          {budgetIsValid ? "Saved in this browser" : "Enter a budget of at least $1"}
        </span>
      </section>

      <section className="dataset-picker">
        <label htmlFor="saved-dataset">Or use a previously uploaded dataset</label>
        <div className="dataset-picker-controls">
          <select
            id="saved-dataset"
            value={selectedDatasetId}
            disabled={datasetListLoading || datasets.length === 0}
            onChange={(event) => {
              const datasetId = event.target.value;
              setSelectedDatasetId(datasetId);
              setActiveDatasetId(datasetId);
              setResult(null);
              setPreview(null);
              setSummary(null);
              setError(null);
            }}
          >
            <option value="">
              {datasetListLoading ? "Loading datasets…" : "Select a dataset"}
            </option>
            {datasets.map((dataset) => {
              const usable = REQUIRED_DATASET_FEATURES.every((feature) =>
                dataset.columns.includes(feature),
              );
              return (
                <option
                  disabled={!usable}
                  key={dataset.dataset_id}
                  value={dataset.dataset_id}
                >
                  {dataset.filename}
                  {usable ? "" : " (missing required features)"}
                </option>
              );
            })}
          </select>
          {selectedDatasetId && (
            <button
              className="btn-secondary"
              onClick={() => navigate("/")}
              type="button"
            >
              Open dashboard
            </button>
          )}
        </div>
        {datasetListError && (
          <p className="dataset-list-error" role="alert">
            Could not load saved datasets: {datasetListError}
          </p>
        )}
        {!datasetListLoading && !datasetListError && datasets.length === 0 && (
          <p className="dataset-list-help">No uploaded datasets found yet.</p>
        )}
        {selectedDatasetId && (
          <p className="dataset-list-help">
            The selected dataset will be used by the dashboard, EDA, and causal
            analysis pages.
          </p>
        )}
      </section>

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
