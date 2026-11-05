import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { GitBranch, Play, Target, TrendingUp, Users } from "lucide-react";
import CausalDag from "../components/CausalDag";
import CausalEvaluationCharts from "../components/CausalEvaluationCharts";
import { ErrorMessage, LoadingSpinner } from "../components/Feedback";
import StatCard from "../components/StatCard";
import {
  fetchCausalDag,
  fetchDatasetDetails,
  getActiveDatasetId,
  getApiErrorMessage,
  identifyCausalEffect,
  trainCausalModel,
} from "../services/api";

const PAGE_SIZE = 50;

export default function ModelAnalysis() {
  const [datasetId, setDatasetId] = useState(getActiveDatasetId);
  useEffect(() => {
    const updateDataset = () => setDatasetId(getActiveDatasetId());
    window.addEventListener("storage", updateDataset);
    window.addEventListener("econocausal:activeDatasetChanged", updateDataset);
    return () => {
      window.removeEventListener("storage", updateDataset);
      window.removeEventListener("econocausal:activeDatasetChanged", updateDataset);
    };
  }, []);

  return <CausalLab key={datasetId ?? "no-dataset"} datasetId={datasetId} />;
}

function CausalLab({ datasetId }) {
  const [datasetDetails, setDatasetDetails] = useState(null);
  const [datasetLoading, setDatasetLoading] = useState(Boolean(datasetId));
  const [datasetError, setDatasetError] = useState(null);
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
    if (!datasetId) {
      return () => {
        active = false;
      };
    }

    const loadActiveDataset = async () => {
      try {
        const details = await fetchDatasetDetails(datasetId);
        if (!active) return;
        setDatasetDetails(details);
        if (details.causal_compatibility.compatible) {
          try {
            const graph = await fetchCausalDag();
            if (active) setDag(graph);
          } catch (requestError) {
            if (active) setDagError(getApiErrorMessage(requestError));
          }
        }
      } catch (requestError) {
        if (active) setDatasetError(getApiErrorMessage(requestError));
      } finally {
        if (active) setDatasetLoading(false);
      }
    };
    loadActiveDataset();
    return () => {
      active = false;
    };
  }, [datasetId]);

  const runIdentification = async () => {
    setIdentifying(true);
    setDagError(null);
    try {
      const identified = await identifyCausalEffect(datasetId);
      if (getActiveDatasetId() === datasetId) setIdentification(identified);
    } catch (requestError) {
      if (getActiveDatasetId() === datasetId) {
        setDagError(getApiErrorMessage(requestError));
      }
    } finally {
      if (getActiveDatasetId() === datasetId) setIdentifying(false);
    }
  };

  const runTraining = async () => {
    setTraining(true);
    setError(null);
    setResult(null);
    setPage(0);
    try {
      const analysis = await trainCausalModel(datasetId);
      if (getActiveDatasetId() === datasetId) setResult(analysis);
    } catch (requestError) {
      if (getActiveDatasetId() === datasetId) {
        setError(getApiErrorMessage(requestError));
      }
    } finally {
      if (getActiveDatasetId() === datasetId) setTraining(false);
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
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            CAMPAIGN ANALYTICS
          </div>
          <h1>Campaign uplift</h1>
          <p>Identify the causal effect, train Double ML, and evaluate out-of-fold uplift.</p>
        </div>
        <Link className="button button-secondary" to="/upload">
          Data workspace
        </Link>
      </div>

      <section className="panel causal-section">
        <div className="panel-heading">
          <div>
            <h2>Selected dataset</h2>
            <p>Preview and schema checks are always tied to the currently selected upload.</p>
          </div>
        </div>
        {!datasetId ? (
          <>
            <p className="causal-note">Choose or upload a dataset before viewing its details or running causal analysis.</p>
            <Link className="button button-secondary" to="/upload">Choose dataset</Link>
          </>
        ) : datasetLoading ? (
          <LoadingSpinner label="Loading selected dataset details…" />
        ) : datasetError ? (
          <ErrorMessage message={datasetError} />
        ) : datasetDetails ? (
          <>
            <div className="model-info">
              <div><strong>Dataset ID</strong><span>{datasetDetails.dataset_id}</span></div>
              <div><strong>Rows</strong><span>{datasetDetails.rows.toLocaleString()}</span></div>
              <div><strong>Columns</strong><span>{datasetDetails.columns.length}</span></div>
              <div><strong>Missing values</strong><span>{datasetDetails.missing_values.toLocaleString()}</span></div>
              <div>
                <strong>Causal schema</strong>
                <span>{datasetDetails.causal_compatibility.compatible ? "Ready for Hillstrom DML" : "Not compatible"}</span>
              </div>
            </div>
            <p className="causal-note">
              Required for this analysis: {datasetDetails.causal_compatibility.required_columns.join(", ")}.
            </p>
            {!datasetDetails.causal_compatibility.compatible && (
              <p className="causal-note">
                This dataset is previewed as uploaded, but causal analysis is disabled because it is missing:{" "}
                {datasetDetails.causal_compatibility.missing_columns.join(", ")}.
              </p>
            )}
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>{datasetDetails.columns.map((column) => <th key={column}>{column}</th>)}</tr>
                </thead>
                <tbody>
                  {datasetDetails.preview.map((row, rowIndex) => (
                    <tr key={`${datasetDetails.dataset_id}-${rowIndex}`}>
                      {datasetDetails.columns.map((column) => (
                        <td key={column}>{row[column] == null ? "—" : String(row[column])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique values</th></tr>
                </thead>
                <tbody>
                  {datasetDetails.column_details.map((column) => (
                    <tr key={column.name}>
                      <td>{column.name}</td><td>{column.dtype}</td>
                      <td>{column.missing_values.toLocaleString()}</td>
                      <td>{column.unique_values.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </section>

      {datasetDetails?.causal_compatibility.compatible && (
        <>
      <section className="panel causal-section">
        <div className="panel-heading">
          <div>
            <h2><GitBranch size={18} aria-hidden="true" /> Causal graph</h2>
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
                  <strong>{identification.estimand_method} estimand</strong>
                  <pre>{identification.identified_estimand}</pre>
                  <small>Adjustment set: {identification.adjustment_set.join(", ")}</small>
                  <small>{identification.warning}</small>
                </div>
              )}
            </div>
          </>
        ) : !dagError && datasetLoading ? <LoadingSpinner label="Loading causal graph…" /> : null}
      </section>

      <section className="panel causal-section">
        <div className="panel-heading">
          <div>
            <h2><TrendingUp size={18} aria-hidden="true" /> Double machine learning</h2>
            <p>Cross-fitted EconML CausalForestDML with random-forest nuisance models and outer-fold out-of-sample evaluation.</p>
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
          Training uses dataset {datasetDetails.dataset_id}. For Hillstrom-compatible data, treatment is Womens E-Mail versus No E-Mail and outcome is conversion; the data does not estimate dollar-discount effects.
        </p>
        {training && <LoadingSpinner label="Fitting cross-fitted causal forest and generating out-of-fold evaluation…" />}
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
              note="Out-of-fold Qini area comparison"
              icon={Target}
            />
          </div>

          <p className="causal-note">
            {result.estimator} · {result.base_estimators} · {result.treatment}. {result.warning}
          </p>
          <div className="model-info">
            <div><strong>Run ID</strong><span>{result.model_id}</span></div>
            <div><strong>Treatment definition</strong><span>{result.treatment}</span></div>
            <div><strong>Evaluation</strong><span>{result.evaluation_method}</span></div>
          </div>

          <CausalEvaluationCharts result={result} />

          <section className="panel causal-section">
            <div className="panel-heading">
              <div>
                <h2>Randomized-trial benchmark</h2>
                <p>Hillstrom randomized assignment provides an independent raw difference-in-means benchmark.</p>
              </div>
            </div>
            <div className="archive-review-stats">
              <div>
                <strong>DML mean ITE</strong>
                <span>{(result.ate * 100).toFixed(2)} pp</span>
              </div>
              <div>
                <strong>RCT difference in means</strong>
                <span>{(result.rct_benchmark.raw_difference * 100).toFixed(2)} pp</span>
              </div>
              <div>
                <strong>RCT 90% confidence interval</strong>
                <span>
                  {(result.rct_benchmark.ci_90_lower * 100).toFixed(2)} to{" "}
                  {(result.rct_benchmark.ci_90_upper * 100).toFixed(2)} pp
                </span>
              </div>
              <div>
                <strong>RCT groups</strong>
                <span>
                  {(result.rct_benchmark.mean_conversion_treated * 100).toFixed(2)}% treated ·{" "}
                  {(result.rct_benchmark.mean_conversion_control * 100).toFixed(2)}% control
                </span>
              </div>
            </div>
            <p className="causal-note">{result.rct_benchmark.design}. The DML estimate and raw randomized contrast are complementary checks, not expected to match exactly.</p>
          </section>

          <section className="panel causal-section">
            <div className="panel-heading">
              <div>
                <h2>Causal audit · DoWhy refutations</h2>
                <p>Robustness checks at α = {result.causal_audit.alpha}; passing does not prove that hidden confounding is absent.</p>
              </div>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr><th>Refuter</th><th>P-value</th><th>Result</th><th>Refuted effect</th></tr>
                </thead>
                <tbody>
                  {result.causal_audit.refutations.map((refutation) => (
                    <tr key={refutation.method}>
                      <td>{refutation.method.replaceAll("_", " ")}</td>
                      <td>{refutation.p_value == null ? "—" : refutation.p_value.toFixed(3)}</td>
                      <td>
                        <span className={`audit-badge audit-${refutation.status}`}>
                          {refutation.status}
                        </span>
                        {refutation.message && <small className="audit-error">{refutation.message}</small>}
                      </td>
                      <td>{refutation.refuted_effect == null ? "—" : `${(refutation.refuted_effect * 100).toFixed(3)} pp`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="causal-note">{result.causal_audit.interpretation}</p>
          </section>

          <section className="panel causal-section">
            <div className="panel-heading">
              <div>
                <h2>Propensity and covariate balance</h2>
                <p>Standardized mean differences before matching, comparing randomized treatment groups.</p>
              </div>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr><th>Covariate</th><th>Largest level difference</th><th>SMD</th><th>Balance check</th></tr>
                </thead>
                <tbody>
                  {result.covariate_balance.map((item) => (
                    <tr key={item.covariate}>
                      <td>{item.covariate}</td>
                      <td>{item.largest_level.replace(/^.*__/, "")}</td>
                      <td>{item.smd.toFixed(3)} (|SMD| {item.absolute_smd.toFixed(3)})</td>
                      <td>{item.balanced ? "Balanced (< 0.10)" : "Review (≥ 0.10)"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="causal-note">Because assignment was randomized, measured covariates should already be balanced. Propensity-score matching may therefore add little and can reduce precision.</p>
          </section>

          <section className="panel causal-section">
            <div className="panel-heading">
              <div>
                <h2>Budget allocation</h2>
                <p>Set the campaign budget and intervention cost to create a constrained customer allocation.</p>
              </div>
              <Link className="button button-primary" to="/allocation">
                Open budget allocation
              </Link>
            </div>
          </section>

          <section className="panel causal-section">
            <div className="panel-heading">
              <div>
                <h2>Customer-level treatment effects</h2>
                <p>
                  {result.customers_scored.toLocaleString()} eligible customers scored. The table contains {result.customer_rows_returned.toLocaleString()} rows
                  {result.customers_scored > result.customer_rows_returned
                    ? ` (20,000-row cap; ${(
                        result.customers_scored - result.customer_rows_returned
                      ).toLocaleString()} scored rows are not filterable here).`
                    : "; filters and pagination cover all scored rows."}
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
                  <tr><th>Row ID</th><th>Treatment group</th><th>Estimated ITE</th><th>90% effect interval</th><th>Effect (percentage points)</th><th>Observed conversion (row outcome only)</th></tr>
                </thead>
                <tbody>
                  {visibleCustomers.map((customer) => (
                    <tr key={customer.row_id}>
                      <td>{customer.row_id}</td>
                      <td>{customer.treatment_group}</td>
                      <td>{customer.ite.toFixed(5)}</td>
                      <td>{(customer.ite_lower_90 * 100).toFixed(2)} to {(customer.ite_upper_90 * 100).toFixed(2)} pp</td>
                      <td>{customer.effect_percentage_points.toFixed(3)}</td>
                      <td>{customer.conversion}</td>
                    </tr>
                  ))}
                  {!visibleCustomers.length && (
                    <tr><td colSpan="6">No customers match these filters.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="causal-note">Observed conversion is the individual row’s factual outcome, not its causal effect. ITEs and their intervals estimate counterfactual differences at the population/model level.</p>
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
        </>
      )}
    </div>
  );
}
