import { useCallback, useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartCard from "./ChartCard";
import { ErrorMessage, LoadingSpinner } from "./Feedback";
import {
  fetchArchiveCampaignReport,
  fetchArchiveCampaignScores,
  getApiErrorMessage,
  trainArchiveCampaignModel,
} from "../services/api";

const PAGE_SIZE = 50;

export default function ArchiveCampaignReview() {
  const [report, setReport] = useState(null);
  const [scores, setScores] = useState(null);
  const [query, setQuery] = useState("");
  const [minimumEffect, setMinimumEffect] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState(null);

  const loadReport = useCallback(async () => {
    try {
      const data = await fetchArchiveCampaignReport();
      setReport(data);
      setError(null);
    } catch (requestError) {
      if (requestError.response?.status === 404) {
        setReport(null);
        setError(null);
      } else {
        setError(getApiErrorMessage(requestError));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchArchiveCampaignReport()
      .then((data) => {
        if (active) setReport(data);
      })
      .catch((requestError) => {
        if (active && requestError.response?.status !== 404) {
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

  useEffect(() => {
    if (!report) return undefined;
    let active = true;
    fetchArchiveCampaignScores({
      offset: page * PAGE_SIZE,
      limit: PAGE_SIZE,
      minimumEffect:
        minimumEffect === "" ? undefined : Number(minimumEffect),
      query: query.trim() || undefined,
    })
      .then((data) => {
        if (active) setScores(data);
      })
      .catch((requestError) => {
        if (active) setError(getApiErrorMessage(requestError));
      });
    return () => {
      active = false;
    };
  }, [minimumEffect, page, query, report]);

  const runTraining = async () => {
    setTraining(true);
    setError(null);
    try {
      const result = await trainArchiveCampaignModel();
      setReport(result.report);
      setScores(null);
      setPage(0);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setTraining(false);
    }
  };

  const refutations = report?.dowhy_audit?.refutations ?? [];
  const curve = report?.holdout_evaluation?.uplift_curve ?? [];
  const pageCount = Math.ceil((scores?.total ?? 0) / PAGE_SIZE);

  return (
    <section className="panel causal-section archive-review">
      <div className="panel-heading">
        <div>
          <h2>Retail archive campaign review</h2>
          <p>
            Uses household campaign assignments and transaction history from
            the local archive, independently of the Hillstrom email dataset.
          </p>
        </div>
        <button
          className="button button-primary"
          type="button"
          onClick={runTraining}
          disabled={training}
        >
          {training ? "Training and auditing…" : report ? "Retrain archive model" : "Train archive model"}
        </button>
      </div>

      <p className="archive-review-warning" role="note">
        The archive has campaign assignments, not assigned $10/$20 discount
        levels. This analysis estimates campaign-assignment effects on household
        sales; it is not a personalized discount model or budget optimizer.
      </p>

      {loading && !report ? (
        <LoadingSpinner label="Checking for a saved archive analysis…" />
      ) : null}
      {training && (
        <LoadingSpinner label="Preparing household data, fitting DML, matching, and running DoWhy refutations…" />
      )}
      {error && <ErrorMessage message={error} onRetry={loadReport} />}
      {!loading && !report && !training && !error && (
        <p className="causal-note">
          No archive model has been trained yet. Training reads the campaign
          archive under <code>backend/data/archive (2)</code> and saves the model
          and review report locally.
        </p>
      )}

      {report && (
        <>
          <div className="archive-review-stats">
            <div><strong>Campaign</strong><span>{report.campaign_id} · {report.campaign_type}</span></div>
            <div><strong>Analysis cohort</strong><span>{report.cohort_rows.toLocaleString()} households</span></div>
            <div><strong>Treated / control</strong><span>{report.treated_households.toLocaleString()} / {report.control_households.toLocaleString()}</span></div>
            <div><strong>Mean DML ITE</strong><span>${report.outcome_mean_ite.toFixed(2)} sales / household</span></div>
            <div><strong>Raw sales difference</strong><span>${report.raw_sales_difference.toFixed(2)} / household</span></div>
            <div><strong>Held-out targeting</strong><span>{report.holdout_evaluation.outperforms_random ? "Above random baseline" : "Did not outperform random"}</span></div>
          </div>

          <ChartCard
            title="Held-out incremental sales curve"
            subtitle="Cumulative estimated sales lift versus a random rollout; evaluation uses a separate 30% holdout."
          >
            <div className="chart-frame">
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={curve}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="population_fraction"
                    tickFormatter={(value) => `${Math.round(value * 100)}%`}
                    tickLine={false}
                    label={{ value: "Households targeted", position: "insideBottom", offset: -3 }}
                  />
                  <YAxis
                    tickLine={false}
                    label={{ value: "Estimated incremental sales ($)", angle: -90, position: "insideLeft" }}
                  />
                  <Tooltip
                    labelFormatter={(value) => `${(value * 100).toFixed(1)}% targeted`}
                    formatter={(value) => `$${Number(value).toFixed(2)}`}
                  />
                  <Line
                    dataKey="strategy_gain"
                    name="DML-ranked targeting"
                    stroke="#4f46e5"
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    dataKey="random_gain"
                    name="Random rollout"
                    stroke="#94a3b8"
                    dot={false}
                    strokeDasharray="5 4"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <div className="archive-review-grid">
            <div>
              <h3>Propensity-score matching diagnostics</h3>
              <p>{report.propensity_matching.method}; {report.propensity_matching.treated_matched.toLocaleString()} treated households matched.</p>
              <p>Max absolute standardized mean difference: {report.propensity_matching.max_abs_smd_before.toFixed(3)} before, {report.propensity_matching.max_abs_smd_after.toFixed(3)} after matching.</p>
              <p>Matched sales difference: ${report.propensity_matching.matched_average_sales_difference.toFixed(2)} per household.</p>
              {report.propensity_matching.max_abs_smd_after > 0.1 && (
                <p className="archive-review-warning">
                  Balance remains imperfect (max |SMD| &gt; 0.1); interpret the
                  matched estimate cautiously.
                </p>
              )}
            </div>
            <div>
              <h3>DoWhy refutation checks</h3>
              <p>
                Linear backdoor estimate: $
                {report.dowhy_audit.linear_backdoor_effect.toFixed(2)} per
                household. Completed {report.dowhy_audit.completed_refutations}
                {" "}/ {refutations.length} checks.
              </p>
              <div className="table-scroll">
                <table className="data-table">
                  <thead><tr><th>Refutation</th><th>Status</th><th>Changed estimate</th><th>p-value</th></tr></thead>
                  <tbody>
                    {refutations.map((item) => (
                      <tr key={item.method}>
                        <td>{item.method.replaceAll("_", " ")}</td>
                        <td>{item.status}</td>
                        <td>{item.refuted_effect == null ? "—" : `$${item.refuted_effect.toFixed(2)}`}</td>
                        <td>{item.p_value == null ? "—" : item.p_value.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="causal-note">{report.dowhy_audit.interpretation}</p>
            </div>
          </div>

          <section className="archive-sensitivity">
            <h3>Unobserved-confounder sensitivity</h3>
            <p>
              Robustness value to reduce the adjusted linear estimate to zero:
              {" "}{(report.unobserved_confounder_sensitivity.robustness_value_to_zero * 100).toFixed(1)}%
              {" "}partial R-squared.
            </p>
            <div className="table-scroll">
              <table className="data-table">
                <thead><tr><th>Partial R² (treatment)</th><th>Partial R² (outcome)</th><th>Adjusted effect bounds</th><th>Includes zero</th></tr></thead>
                <tbody>
                  {report.unobserved_confounder_sensitivity.scenarios.map((scenario) => (
                    <tr key={scenario.partial_r2_treatment}>
                      <td>{(scenario.partial_r2_treatment * 100).toFixed(0)}%</td>
                      <td>{(scenario.partial_r2_outcome * 100).toFixed(0)}%</td>
                      <td>
                        ${scenario.lower_effect_bound.toFixed(2)} to $
                        {scenario.upper_effect_bound.toFixed(2)}
                      </td>
                      <td>{scenario.includes_zero ? "Yes" : "No"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="causal-note">
              {report.unobserved_confounder_sensitivity.interpretation}
            </p>
          </section>

          <section className="archive-score-section">
            <div className="archive-score-heading">
              <div>
                <h3>Household-level estimated effects</h3>
                <p>{(scores?.total ?? 0).toLocaleString()} matching households · ranked by estimated sales effect</p>
              </div>
              <div className="causal-filters">
                <input
                  aria-label="Filter by household ID"
                  placeholder="Household ID"
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setPage(0);
                  }}
                />
                <input
                  aria-label="Minimum estimated sales effect"
                  type="number"
                  step="0.01"
                  placeholder="Minimum effect ($)"
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
                <thead><tr><th>Rank</th><th>Household</th><th>Campaign assigned</th><th>Observed sales</th><th>Estimated sales effect</th></tr></thead>
                <tbody>
                  {(scores?.scores ?? []).map((score) => (
                    <tr key={score.household_key}>
                      <td>{score.effect_rank}</td>
                      <td>{score.household_key}</td>
                      <td>{score.treatment_assigned ? "Yes" : "No"}</td>
                      <td>${score.campaign_sales.toFixed(2)}</td>
                      <td>${score.estimated_sales_effect.toFixed(2)}</td>
                    </tr>
                  ))}
                  {scores && scores.scores.length === 0 && (
                    <tr><td colSpan="5">No households match these filters.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="causal-pagination">
              <span>{scores?.total ?? 0} matching households · Page {pageCount ? page + 1 : 0} of {pageCount}</span>
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
                  disabled={!pageCount || page >= pageCount - 1}
                >
                  Next
                </button>
              </div>
            </div>
          </section>

          <ul className="archive-review-caveats">
            {report.caveats.map((caveat) => <li key={caveat}>{caveat}</li>)}
          </ul>
        </>
      )}
    </section>
  );
}
