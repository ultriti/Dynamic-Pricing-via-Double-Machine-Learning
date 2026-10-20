import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Database, Eye, Upload, Users } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartCard from "../components/ChartCard";
import { EmptyState as Empty, ErrorMessage, LoadingSpinner } from "../components/Feedback";
import StatCard from "../components/StatCard";
import { fetchDatasetSummary, getApiErrorMessage } from "../services/api";

function HomePage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadSummary = useCallback(async () => {
    try {
      setSummary(await fetchDatasetSummary());
    } catch (requestError) {
      if (requestError.response?.status === 404) {
        setSummary(null);
      } else {
        setError(getApiErrorMessage(requestError));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchDatasetSummary()
      .then((data) => {
        if (active) setSummary(data);
      })
      .catch((requestError) => {
        if (!active) return;
        if (requestError.response?.status !== 404) {
          setError(getApiErrorMessage(requestError));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const refreshSummary = () => {
    setLoading(true);
    setError(null);
    loadSummary();
  };

  const treatmentGroups = Object.entries(summary?.treatment_group_counts ?? {}).map(
    ([name, customers]) => ({ name, customers }),
  );

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <h1>EconoCausal Dashboard</h1>
          <p>Explore customer data and prepare datasets for causal inference analysis.</p>
        </div>
        <Link className="button button-primary" to="/upload">
          <Upload size={17} aria-hidden="true" /> Upload dataset
        </Link>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : error ? (
        <section className="panel dashboard-empty">
          <ErrorMessage message={error} onRetry={refreshSummary} />
        </section>
      ) : summary ? (
        <>
          <div className="stats-grid">
            <StatCard label="Total Customers" value={summary.rows?.toLocaleString() ?? "—"} icon={Users} />
            <StatCard label="Conversion Rate" value={summary.conversion_rate_percent == null ? "—" : `${summary.conversion_rate_percent}%`} note="Observed conversions" icon={Database} />
            <StatCard label="Total Spend" value={summary.total_spend == null ? "—" : `$${Number(summary.total_spend).toLocaleString()}`} icon={Database} />
            <StatCard label="Visit Rate" value={summary.visit_rate_percent == null ? "—" : `${summary.visit_rate_percent}%`} note="Observed visits" icon={Eye} />
          </div>

          <div className="dashboard-grid">
            <ChartCard
              title="Marketing treatment groups"
              subtitle="Customer counts by email campaign segment"
            >
              {treatmentGroups.length ? (
                <div className="chart-frame">
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={treatmentGroups} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="name" tickLine={false} />
                      <YAxis allowDecimals={false} tickLine={false} />
                      <Tooltip />
                      <Bar dataKey="customers" fill="#4f46e5" radius={[5, 5, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <Empty title="Treatment groups unavailable" />
              )}
            </ChartCard>

            <section className="panel dataset-status">
              <div className="panel-heading">
                <div>
                  <h2>Dataset status</h2>
                  <p>Current dataset overview</p>
                </div>
                <Database size={19} aria-hidden="true" />
              </div>
              <dl className="status-list">
                <div><dt>Status</dt><dd><span className="status-pill">Dataset uploaded</span></dd></div>
                <div><dt>Dimensions</dt><dd>{summary.rows?.toLocaleString()} rows × {summary.columns} columns</dd></div>
                <div><dt>Missing values</dt><dd>{summary.missing_values?.toLocaleString() ?? "—"}</dd></div>
                <div><dt>Average spend</dt><dd>{summary.average_spend == null ? "—" : `$${Number(summary.average_spend).toLocaleString()}`}</dd></div>
              </dl>
              <div className="inline-actions">
                <Link className="button button-secondary" to="/preview"><Eye size={16} /> Preview data</Link>
                <Link className="button button-secondary" to="/eda">Explore EDA <ArrowRight size={16} /></Link>
              </div>
            </section>
          </div>
          <p className="causal-note">
            This dataset describes email marketing campaigns. It does not measure the causal effect of specific discount amounts.
          </p>
        </>
      ) : (
        <section className="panel dashboard-empty">
          <Empty title="Upload a dataset to get started">
            Dashboard statistics and charts will appear here after you upload a valid Hillstrom CSV.
          </Empty>
          <Link className="button button-primary" to="/upload"><Upload size={17} /> Upload dataset</Link>
        </section>
      )}
    </div>
  );
}

export default HomePage;
