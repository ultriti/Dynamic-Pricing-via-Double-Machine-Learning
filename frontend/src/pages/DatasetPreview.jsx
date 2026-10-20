import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw, Upload } from "lucide-react";
import DataTable from "../components/DataTable";
import { EmptyState, ErrorMessage, LoadingSpinner } from "../components/Feedback";
import {
  fetchDatasetPreview,
  getApiErrorMessage,
} from "../services/api";

export default function DatasetPreview() {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadPreview = useCallback(async () => {
    try {
      setPreview(await fetchDatasetPreview());
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchDatasetPreview()
      .then((data) => {
        if (active) setPreview(data);
      })
      .catch((requestError) => {
        if (active) setError(getApiErrorMessage(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const refreshPreview = () => {
    setLoading(true);
    setError(null);
    loadPreview();
  };

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <h1>Dataset Preview</h1>
          <p>Inspect the first 10 rows without loading the full dataset into the browser.</p>
        </div>
        <button className="button button-secondary" onClick={refreshPreview} type="button">
          <RefreshCw size={16} aria-hidden="true" /> Refresh
        </button>
      </div>
      {loading ? <LoadingSpinner /> : error ? (
        <section className="panel dashboard-empty">
          <ErrorMessage message={error} onRetry={refreshPreview} />
          <Link className="button button-primary" to="/upload"><Upload size={16} /> Upload a dataset</Link>
        </section>
      ) : preview ? (
        <>
          <div className="preview-meta">
            <span><strong>{preview.rows?.toLocaleString()}</strong> total rows</span>
            <span><strong>{preview.columns?.length}</strong> columns</span>
            <span>Showing first {preview.data?.length ?? 0} rows</span>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <div><h2>Column names</h2><p>{preview.columns?.join(", ")}</p></div>
            </div>
            <DataTable columns={preview.columns} rows={preview.data} />
          </section>
          {!preview.data?.length && <EmptyState title="This dataset has no preview rows" />}
        </>
      ) : <EmptyState />}
    </div>
  );
}
