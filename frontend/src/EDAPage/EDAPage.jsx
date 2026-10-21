import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import "./EDAPage.css";

const API = "http://localhost:8000";

const EDAPage = () => {
  const [summary, setSummary] = useState(null);
  const [preview, setPreview] = useState(null);
  const [correlation, setCorrelation] = useState(null);
  const [selectedCol, setSelectedCol] = useState("recency");
  const [distribution, setDistribution] = useState(null);
  const [valueCounts, setValueCounts] = useState(null);
  const [vcColumn, setVcColumn] = useState("segment");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const categoricalCols = ["history_segment", "zip_code", "channel", "segment"];
  const numericCols = ["recency", "history", "mens", "womens", "newbie", "visit", "conversion", "spend"];

  useEffect(() => { fetchAll(); }, []);

  useEffect(() => {
    if (!loading && !error) fetchDistribution(selectedCol);
  }, [selectedCol]);

  useEffect(() => {
    if (!loading && !error) fetchValueCounts(vcColumn);
  }, [vcColumn]);

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [s, p, c] = await Promise.all([
        fetch(`${API}/api/dataset/summary`),
        fetch(`${API}/api/dataset/preview`),
        fetch(`${API}/api/dataset/correlation`),
      ]);
      if (!s.ok) throw new Error("No dataset uploaded. Upload a file first.");
      setSummary(await s.json());
      setPreview(await p.json());
      setCorrelation(await c.json());
      await fetchDistribution("recency");
      await fetchValueCounts("segment");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchDistribution = async (col) => {
    try {
      const r = await fetch(`${API}/api/dataset/distribution/${col}`);
      if (r.ok) setDistribution(await r.json());
    } catch (e) { /* ignore */ }
  };

  const fetchValueCounts = async (col) => {
    try {
      const r = await fetch(`${API}/api/dataset/value-counts/${col}`);
      if (r.ok) setValueCounts(await r.json());
    } catch (e) { /* ignore */ }
  };

  if (loading) {
    return (
      <div className="eda">
        <h1 className="page-title">Analysis</h1>
        <p className="page-desc">Loading…</p>
        <div className="loader-wrap"><div className="loader"></div></div>
      </div>
    );
  }

  if (error) {
  return (
    <div className="eda">
      <h1 className="page-title">Analysis</h1>
      <p className="page-desc">Exploratory data analysis</p>
      <div className="empty" style={{ textAlign: 'center', padding: '40px', backgroundColor: '#fff', borderRadius: '12px', border: '1px solid #e0e0e0' }}>
        <div style={{ fontSize: '40px', marginBottom: '20px' }}>🔌</div>
        <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px' }}>No Data Connected</h3>
        <p style={{ color: '#666', marginBottom: '20px' }}>
          We couldn't reach the server. Please make sure the backend is running and you have uploaded a dataset.
        </p>
        <Link to="/upload" className="btn-primary" style={{ padding: '10px 20px', textDecoration: 'none' }}>
          Go to Upload Page
        </Link>
      </div>
    </div>
  );
}
  const maxCorr = correlation ? Math.max(
    ...correlation.columns.flatMap((c1) =>
      correlation.columns.map((c2) => Math.abs(correlation.data[c1]?.[c2] || 0))
    )
  ) : 1;

  return (
    <div className="eda">
      <h1 className="page-title">Analysis</h1>
      <p className="page-desc">Exploratory data analysis</p>

      {/* KPI Row */}
      {summary && (
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-label">Customers</span>
            <span className="kpi-value">{summary.total_customers?.toLocaleString()}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">Columns</span>
            <span className="kpi-value">{summary.total_columns}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">Conversion rate</span>
            <span className="kpi-value">{summary.conversion_rate}%</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">Total spend</span>
            <span className="kpi-value">${summary.total_spend?.toLocaleString()}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">Visit rate</span>
            <span className="kpi-value">{summary.visit_rate}%</span>
          </div>
        </div>
      )}

      {/* Two-column layout */}
      <div className="grid-2">
        {/* Treatment Groups */}
        {summary?.treatment_groups && (
          <div className="card">
            <div className="card-head">Treatment groups</div>
            <div className="hbar-chart">
              {Object.entries(summary.treatment_groups).map(([label, count]) => {
                const max = Math.max(...Object.values(summary.treatment_groups));
                return (
                  <div key={label} className="hbar-row">
                    <span className="hbar-label">{label}</span>
                    <div className="hbar-track">
                      <div className="hbar-fill" style={{ width: `${(count / max) * 100}%` }}></div>
                    </div>
                    <span className="hbar-val">{count.toLocaleString()}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Value Counts */}
        <div className="card">
          <div className="card-head">
            <span>Value counts</span>
            <select className="sel" value={vcColumn} onChange={(e) => setVcColumn(e.target.value)}>
              {categoricalCols.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          {valueCounts && (
            <div className="hbar-chart">
              {Object.entries(valueCounts.counts).map(([label, count]) => {
                const max = Math.max(...Object.values(valueCounts.counts));
                return (
                  <div key={label} className="hbar-row">
                    <span className="hbar-label">{label}</span>
                    <div className="hbar-track">
                      <div className="hbar-fill alt" style={{ width: `${(count / max) * 100}%` }}></div>
                    </div>
                    <span className="hbar-val">{count.toLocaleString()}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Distribution */}
      <div className="card">
        <div className="card-head">
          <span>Distribution</span>
          <select className="sel" value={selectedCol} onChange={(e) => setSelectedCol(e.target.value)}>
            {[...numericCols, ...categoricalCols].map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        {distribution && (
          <div className="vbar-chart">
            {distribution.labels.map((label, i) => {
              const max = Math.max(...distribution.values);
              const pct = max > 0 ? (distribution.values[i] / max) * 100 : 0;
              return (
                <div key={i} className="vbar-col" title={`${label}: ${distribution.values[i].toLocaleString()}`}>
                  <span className="vbar-val">{distribution.values[i].toLocaleString()}</span>
                  <div className="vbar-track">
                    <div className="vbar-fill" style={{ height: `${pct}%` }}></div>
                  </div>
                  <span className="vbar-label">{label.length > 10 ? label.slice(0, 10) + "…" : label}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Correlation */}
      {correlation && (
        <div className="card">
          <div className="card-head">Correlation matrix</div>
          <div className="corr-scroll">
            <table className="corr-tbl">
              <thead>
                <tr>
                  <th></th>
                  {correlation.columns.map((c) => <th key={c} className="corr-th">{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {correlation.columns.map((row) => (
                  <tr key={row}>
                    <td className="corr-rl">{row}</td>
                    {correlation.columns.map((col) => {
                      const v = correlation.data[col]?.[row] || 0;
                      const abs = Math.abs(v);
                      const op = Math.min(abs / maxCorr, 1);
                      const bg = v >= 0
                        ? `rgba(37,99,235,${op * 0.5})`
                        : `rgba(220,38,38,${op * 0.5})`;
                      return (
                        <td key={col} className="corr-cell" style={{ background: bg }} title={`${row} × ${col}`}>
                          {v}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Preview */}
      {preview && (
        <div className="card">
          <div className="card-head">Data preview</div>
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
    </div>
  );
};

export default EDAPage;
