import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart3, Database, Users } from "lucide-react";
import { EmptyState, ErrorMessage, LoadingSpinner } from "../components/Feedback";
import StatCard from "../components/StatCard";
import AllocationMatrix from "../components/AllocationMatrix";
import UpliftChart from "../components/UpliftChart";
import { fetchModelPredictions, fetchModelStatus, getApiErrorMessage } from "../services/api";

export default function ModelAnalysis() {
  const [result, setResult] = useState(null);
  const [trained, setTrained] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadResults = useCallback(async () => {
    try {
      const status = await fetchModelStatus();
      setTrained(Boolean(status.exists));
      if (status.exists) {
        setResult(await fetchModelPredictions());
      } else {
        setResult(null);
      }
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchModelStatus()
      .then((status) => {
        if (!active) return null;
        setTrained(Boolean(status.exists));
        return status.exists ? fetchModelPredictions() : null;
      })
      .then((data) => {
        if (active && data) setResult(data);
      })
      .catch((requestError) => {
        if (active) {
          setError(getApiErrorMessage(requestError));
          setResult(null);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const refreshResults = () => {
    setLoading(true);
    setError(null);
    loadResults();
  };

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <h1>Saved Model Analysis</h1>
          <p>Separate from Week 2 EDA; predictions are shown only when the saved model and dataset are compatible.</p>
        </div>
        <button className="button button-secondary" onClick={refreshResults} type="button">Refresh</button>
      </div>
      {loading ? <LoadingSpinner label="Checking saved models and dataset..." /> : error ? (
        <section className="panel dashboard-empty">
          <ErrorMessage message={error} onRetry={refreshResults} />
          <Link className="button button-primary" to="/upload">Upload a dataset</Link>
        </section>
      ) : !trained ? (
        <section className="panel dashboard-empty">
          <EmptyState title="No saved model is available">
            This area does not generate or fabricate model results. Train and save a compatible model before requesting estimates.
          </EmptyState>
        </section>
      ) : result ? (
        <>
          <div className="stats-grid">
            <StatCard label="Scored Customers" value={result.customers_scored?.toLocaleString() ?? "—"} icon={Users} />
            <StatCard label="Mean ITE" value={result.mean_ite == null ? "—" : Number(result.mean_ite).toFixed(4)} note={result.treatment} icon={BarChart3} />
            <StatCard label="Positive Estimates" value={result.positive_effect_count?.toLocaleString() ?? "—"} icon={Database} />
            <StatCard label="Negative Estimates" value={result.negative_effect_count?.toLocaleString() ?? "—"} icon={Database} />
          </div>
          <p className="causal-note">
            Model output for {result.outcome ?? "the configured outcome"} under {result.treatment ?? "the configured treatment"}. Estimates depend on the training pipeline and are not discount recommendations.
          </p>
          <UpliftChart customers={result.customers ?? []} />
          <AllocationMatrix customers={result.customers ?? []} />
        </>
      ) : <EmptyState title="No model predictions are available" />}
    </div>
  );
}
