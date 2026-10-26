import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { GitBranch, Play, Target, TrendingUp, Users } from "lucide-react";
import CausalDag from "../components/CausalDag";
import CausalEvaluationCharts from "../components/CausalEvaluationCharts";
import { ErrorMessage, LoadingSpinner } from "../components/Feedback";
import StatCard from "../components/StatCard";
import {
  fetchCausalDag,
  getApiErrorMessage,
  identifyCausalEffect,
  trainCausalModel,
} from "../services/api";

const PAGE_SIZE = 50;

export default function ModelAnalysis() {
  const [dag, setDag] = useState(null);
  const [dagError, setDagError] = useState(null);
  const [identification, setIdentification] = useState(null);
  const [identifying, setIdentifying] = useState(false);
  const [result, setResult] = useState(null);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("");
  const [minimumEffect, setMinimumEffect] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    let active = true;
    fetchCausalDag()
      .then((data) => {
        if (active) setDag(data);
      })
      .catch((requestError) => {
        if (active) setDagError(getApiErrorMessage(requestError));
      });
    return () => {
      active = false;
    };
  }, []);

  const runIdentification = async () => {
    setIdentifying(true);
    setDagError(null);
    try {
      setIdentification(await identifyCausalEffect());
    } catch (requestError) {
      setDagError(getApiErrorMessage(requestError));
    } finally {
      setIdentifying(false);
    }
  };

  const runTraining = async () => {
    setTraining(true);
    setError(null);
    setResult(null);
    setPage(0);
    try {
      setResult(await trainCausalModel());
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setTraining(false);
    }
  };

  const customers = useMemo(() => result?.customers ?? [], [result]);
  const filteredCustomers = useMemo(() => {
    const query = filter.trim().toLowerCase();
    const effectFloor = minimumEffect === "" ? null : Number(minimumEffect);
    return customers.filter((customer) => {
      const matchesQuery =
        !query ||
        customer.row_id.toLowerCase().includes(query) ||
        customer.treatment_group.toLowerCase().includes(query);
      const matchesEffect =
        effectFloor === null ||
        (Number.isFinite(effectFloor) && customer.ite >= effectFloor);
      return matchesQuery && matchesEffect;
    });
  }, [customers, filter, minimumEffect]);
  const pageCount = Math.ceil(filteredCustomers.length / PAGE_SIZE);
  const visibleCustomers = filteredCustomers.slice(
    page * PAGE_SIZE,
    (page + 1) * PAGE_SIZE,
  );

  return (
    <div className="page causal-page">
      <div className="page-heading">
        <div>
          <h1>Causal Lab</h1>
          <p>Weeks 1–2 · Define the causal graph, train Double ML, and evaluate held-out uplift.</p>
        </div>
        <Link className="button button-secondary" to="/upload">
          Upload campaign data
        </Link>
      </div>

      <section className="panel causal-section">
        <div className="panel-heading">
          <div>
            <h2><GitBranch size={18} aria-hidden="true" /> Week 1 · Causal graph</h2>
            <p>Confounders affect both campaign assignment and conversion; post-treatment visits are excluded.</p>
          </div>
        </div>
        {dagError && <ErrorMessage message={dagError} />}
        {dag ? (
          <>
            <CausalDag nodes={dag.nodes} edges={dag.edges} />
            <div className="dag-legend" aria-label="Causal graph node types">
              <span><i className="legend-confounder" /> Confounders</span>
              <span><i className="legend-treatment" /> Treatment</span>
              <span><i className="legend-outcome" /> Outcome</span>
              <span className="dag-treatment">
                Treatment: {dag.treatment} · Outcome: {dag.outcome}
              </span>
            </div>
            <p className="causal-note">{dag.note} The DoWhy estimand depends on these assumptions.</p>
            <div className="causal-actions">
              <button
                className="button button-secondary"
                type="button"
                onClick={runIdentification}
                disabled={identifying}
              >
                {identifying ? "Identifying estimand…" : "Identify effect with DoWhy"}
              </button>
              {identification && (
                <div className="estimand-result">
                  <strong>DoWhy identified estimand</strong>
                  <pre>{identification.identified_estimand}</pre>
                  <small>{identification.warning}</small>
                </div>
              )}
            </div>
          </>
        ) : !dagError ? <LoadingSpinner label="Loading causal graph…" /> : null}
      </section>

      <section className="panel causal-section">
        <div className="panel-heading">
          <div>
            <h2><TrendingUp size={18} aria-hidden="true" /> Week 2 · Double Machine Learning</h2>
            <p>Cross-fitted EconML CausalForestDML with random-forest nuisance models and a held-out evaluation split.</p>
          </div>
          <button
            className="button button-primary"
            type="button"
            onClick={runTraining}
            disabled={training}
          >
            <Play size={15} aria-hidden="true" />
            {training ? "Training model…" : result ? "Retrain on active dataset" : "Train DML model"}
          </button>
        </div>
        <p className="causal-note">
          This mock retail analysis compares Womens E-Mail with No E-Mail for conversion. The Hillstrom data does not contain discount amounts, so these results do not estimate $10 vs $20 discount effects.
        </p>
        {training && <LoadingSpinner label="Fitting cross-fitted causal forest and scoring held-out customers…" />}
        {error && <ErrorMessage message={error} />}
      </section>

      {result && (
        <>
          <div className="stats-grid">
            <StatCard
              label="Customers scored"
              value={result.customers_scored.toLocaleString()}
              note="Eligible comparison cohort"
              icon={Users}
            />
            <StatCard
              label="Mean estimated ITE"
              value={`${(result.mean_ite * 100).toFixed(2)} pp`}
              note="Conversion probability difference"
              icon={TrendingUp}
            />
            <StatCard
              label="Qini coefficient"
              value={result.qini_coefficient.toFixed(2)}
              note="Area above random baseline"
              icon={Target}
            />
            <StatCard
              label="Compared with random"
              value={result.outperforms_random ? "Above baseline" : "Not above baseline"}
              note="Held-out Qini area comparison"
              icon={Target}
            />
          </div>

          <p className="causal-note">
            {result.estimator} · {result.base_estimators} · {result.treatment}. {result.warning}
          </p>

          <CausalEvaluationCharts result={result} />

          <section className="panel causal-section">
            <div className="panel-heading">
              <div>
                <h2>Customer-level treatment effects</h2>
                <p>
                  {result.customers_scored.toLocaleString()} eligible customers scored · {result.customer_rows_returned.toLocaleString()} rows available for filtering
                </p>
              </div>
              <div className="causal-filters">
                <input
                  aria-label="Filter customers by row ID or treatment"
                  placeholder="Filter row or treatment"
                  value={filter}
                  onChange={(event) => {
                    setFilter(event.target.value);
                    setPage(0);
                  }}
                />
                <input
                  aria-label="Minimum estimated treatment effect"
                  type="number"
                  step="0.001"
                  placeholder="Minimum ITE"
                  value={minimumEffect}
                  onChange={(event) => {
                    setMinimumEffect(event.target.value);
                    setPage(0);
                  }}
                />
              </div>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr><th>Row ID</th><th>Treatment group</th><th>Estimated ITE</th><th>Effect (percentage points)</th><th>Observed conversion</th></tr>
                </thead>
                <tbody>
                  {visibleCustomers.map((customer) => (
                    <tr key={customer.row_id}>
                      <td>{customer.row_id}</td>
                      <td>{customer.treatment_group}</td>
                      <td>{customer.ite.toFixed(5)}</td>
                      <td>{customer.effect_percentage_points.toFixed(3)}</td>
                      <td>{customer.conversion}</td>
                    </tr>
                  ))}
                  {!visibleCustomers.length && (
                    <tr><td colSpan="5">No customers match these filters.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="causal-pagination">
              <span>{filteredCustomers.length.toLocaleString()} matching customers · Page {pageCount ? page + 1 : 0} of {pageCount}</span>
              <div>
                <button
                  className="button button-secondary"
                  type="button"
                  onClick={() => setPage((current) => Math.max(0, current - 1))}
                  disabled={page === 0}
                >
                  Previous
                </button>
                <button
                  className="button button-secondary"
                  type="button"
                  onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))}
                  disabled={page >= pageCount - 1}
                >
                  Next
                </button>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
