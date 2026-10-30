import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartCard from "../components/ChartCard";
import {
  EmptyState,
  ErrorMessage,
  LoadingSpinner,
} from "../components/Feedback";
import StatCard from "../components/StatCard";
import {
  fetchColumnDistribution,
  fetchColumnStatistics,
  fetchCorrelationMatrix,
  fetchDatasetSummary,
  fetchScatterPlot,
  fetchValueCounts,
  getApiErrorMessage,
} from "../services/api";
import "./EDAPage.css";

const asChartData = (result) =>
  result.labels.map((label, index) => ({ label, count: result.values[index] }));

function EDAPage() {
  const [summary, setSummary] = useState(null);
  const [columnStats, setColumnStats] = useState(null);
  const [correlation, setCorrelation] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState(null);
  const [ready, setReady] = useState(false);
  const [selectedColumn, setSelectedColumn] = useState("history");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [distributionState, setDistributionState] = useState(null);
  const [valueCountsState, setValueCountsState] = useState(null);
  const [xColumn, setXColumn] = useState("history");
  const [yColumn, setYColumn] = useState("spend");
  const [scatterState, setScatterState] = useState(null);

  const loadOverview = useCallback(async () => {
    try {
      const [datasetSummary, stats, matrix] = await Promise.all([
        fetchDatasetSummary(),
        fetchColumnStatistics(),
        fetchCorrelationMatrix(),
      ]);
      setSummary(datasetSummary);
      setColumnStats(stats);
      setCorrelation(matrix);
      setReady(true);
    } catch (error) {
      setOverviewError(getApiErrorMessage(error));
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetchDatasetSummary(),
      fetchColumnStatistics(),
      fetchCorrelationMatrix(),
    ])
      .then(([datasetSummary, stats, matrix]) => {
        if (!active) return;
        setSummary(datasetSummary);
        setColumnStats(stats);
        setCorrelation(matrix);
        setReady(true);
      })
      .catch((error) => {
        if (active) setOverviewError(getApiErrorMessage(error));
      })
      .finally(() => {
        if (active) setOverviewLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const numericColumns = useMemo(
    () =>
      Object.entries(columnStats?.stats ?? {})
        .filter(([, metrics]) => Object.hasOwn(metrics, "mean"))
        .map(([column]) => column),
    [columnStats],
  );

  const categoricalColumns = useMemo(
    () =>
      Object.keys(columnStats?.stats ?? {}).filter(
        (column) => !numericColumns.includes(column),
      ),
    [columnStats, numericColumns],
  );
  const statisticsMetrics = useMemo(
    () =>
      Array.from(
        new Set(
          Object.values(columnStats?.stats ?? {}).flatMap((metrics) =>
            Object.keys(metrics),
          ),
        ),
      ),
    [columnStats],
  );
  const categoricalColumn = categoricalColumns.includes(selectedCategory)
    ? selectedCategory
    : (categoricalColumns[0] ?? "");

  useEffect(() => {
    if (!ready || !selectedColumn) return;
    let active = true;
    fetchColumnDistribution(selectedColumn)
      .then((result) => {
        if (active) setDistributionState({ column: selectedColumn, result });
      })
      .catch((error) => {
        if (active)
          setDistributionState({
            column: selectedColumn,
            error: getApiErrorMessage(error),
          });
      });
    return () => {
      active = false;
    };
  }, [ready, selectedColumn]);

  useEffect(() => {
    if (!ready || !categoricalColumn) return;
    let active = true;
    fetchValueCounts(categoricalColumn)
      .then((result) => {
        if (active) setValueCountsState({ column: categoricalColumn, result });
      })
      .catch((error) => {
        if (active)
          setValueCountsState({
            column: categoricalColumn,
            error: getApiErrorMessage(error),
          });
      });
    return () => {
      active = false;
    };
  }, [ready, categoricalColumn]);

  useEffect(() => {
    if (!ready || !xColumn || !yColumn) return;
    let active = true;
    fetchScatterPlot(xColumn, yColumn, 500)
      .then((result) => {
        if (active) setScatterState({ key: `${xColumn}-${yColumn}`, result });
      })
      .catch((error) => {
        if (active)
          setScatterState({
            key: `${xColumn}-${yColumn}`,
            error: getApiErrorMessage(error),
          });
      });
    return () => {
      active = false;
    };
  }, [ready, xColumn, yColumn]);

  if (overviewLoading) {
    return (
      <div className="page">
        <h1>Exploratory Analysis</h1>
        <LoadingSpinner />
      </div>
    );
  }

  if (overviewError) {
    return (
      <div className="page">
        <div className="page-heading">
          <div>
            <h1>Exploratory Analysis</h1>
            <p>Explore the uploaded customer dataset.</p>
          </div>
        </div>
        <section className="panel dashboard-empty">
          <ErrorMessage message={overviewError} onRetry={loadOverview} />
          <Link className="button button-primary" to="/upload">
            Upload a dataset
          </Link>
        </section>
      </div>
    );
  }

  const distributionLoading =
    !distributionState || distributionState.column !== selectedColumn;
  const distribution =
    distributionState?.column === selectedColumn
      ? distributionState.result
      : null;
  const distributionError =
    distributionState?.column === selectedColumn
      ? distributionState.error
      : null;
  const scatterKey = `${xColumn}-${yColumn}`;
  const scatterLoading = !scatterState || scatterState.key !== scatterKey;
  const scatter = scatterState?.key === scatterKey ? scatterState.result : null;
  const scatterError =
    scatterState?.key === scatterKey ? scatterState.error : null;
  const distributionData = distribution ? asChartData(distribution) : [];
  const correlationColumns = correlation?.columns ?? [];
  const valueCountsLoading =
    !valueCountsState || valueCountsState.column !== categoricalColumn;
  const valueCounts =
    valueCountsState?.column === categoricalColumn
      ? valueCountsState.result
      : null;
  const valueCountsError =
    valueCountsState?.column === categoricalColumn
      ? valueCountsState.error
      : null;
  const valueCountsData = Object.entries(valueCounts?.counts ?? {})
    .map(([label, count]) => ({ label, count }))
    .sort((left, right) => right.count - left.count)
    .slice(0, 20);

  const refreshOverview = () => {
    setOverviewLoading(true);
    setOverviewError(null);
    setReady(false);
    loadOverview();
  };

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <h1>Exploratory Analysis</h1>
          <p>
            Descriptive statistics and visualizations from the uploaded dataset.
          </p>
        </div>
        <button
          className="button button-secondary"
          onClick={refreshOverview}
          type="button"
        >
          Refresh
        </button>
      </div>

      <div className="stats-grid stats-grid-four">
        <StatCard label="Rows" value={summary.rows?.toLocaleString() ?? "—"} />
        <StatCard label="Columns" value={summary.columns ?? "—"} />
        <StatCard
          label="Missing Values"
          value={summary.missing_values?.toLocaleString() ?? "—"}
        />
        <StatCard
          label="Conversion Rate"
          value={
            summary.conversion_rate_percent == null
              ? "—"
              : `${summary.conversion_rate_percent}%`
          }
        />
      </div>

      <div className="analysis-grid">
        <ChartCard
          title="Marketing treatment groups"
          subtitle="Counts by the observed email campaign segment"
        >
          {Object.keys(summary.treatment_group_counts ?? {}).length ? (
            <div className="chart-frame">
              <ResponsiveContainer width="100%" height={270}>
                <BarChart
                  data={Object.entries(summary.treatment_group_counts).map(
                    ([name, customers]) => ({ name, customers }),
                  )}
                  margin={{ top: 8, right: 12, left: 0, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tickLine={false} />
                  <YAxis allowDecimals={false} tickLine={false} />
                  <Tooltip />
                  <Bar
                    dataKey="customers"
                    fill="#4f46e5"
                    radius={[5, 5, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No treatment group data" />
          )}
        </ChartCard>

        <ChartCard
          title="Numerical distribution"
          subtitle="Histogram bins returned by the distribution API"
          action={
            <select
              aria-label="Select numerical column"
              className="select-control"
              onChange={(event) => setSelectedColumn(event.target.value)}
              value={selectedColumn}
            >
              {numericColumns.map((column) => (
                <option key={column} value={column}>
                  {column}
                </option>
              ))}
            </select>
          }
        >
          {distributionLoading ? (
            <LoadingSpinner />
          ) : distributionError ? (
            <ErrorMessage message={distributionError} />
          ) : !distributionData.length ? (
            <EmptyState title="No distribution data" />
          ) : (
            <div className="chart-frame">
              <ResponsiveContainer width="100%" height={270}>
                <BarChart
                  data={distributionData}
                  margin={{ top: 8, right: 12, left: 0, bottom: 38 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="label"
                    angle={-25}
                    textAnchor="end"
                    interval="preserveStartEnd"
                    tickLine={false}
                  />
                  <YAxis allowDecimals={false} tickLine={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Categorical value counts"
          subtitle="Most frequent values returned by the value-counts API"
          action={
            categoricalColumns.length > 0 && (
              <select
                aria-label="Select categorical column"
                className="select-control"
                onChange={(event) => setSelectedCategory(event.target.value)}
                value={categoricalColumn}
              >
                {categoricalColumns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            )
          }
        >
          {!categoricalColumns.length ? (
            <EmptyState title="No categorical columns" />
          ) : valueCountsLoading ? (
            <LoadingSpinner />
          ) : valueCountsError ? (
            <ErrorMessage message={valueCountsError} />
          ) : !valueCountsData.length ? (
            <EmptyState title="No values to count" />
          ) : (
            <div className="chart-frame">
              <ResponsiveContainer width="100%" height={270}>
                <BarChart
                  data={valueCountsData}
                  margin={{ top: 8, right: 12, left: 0, bottom: 38 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="label"
                    angle={-25}
                    textAnchor="end"
                    interval="preserveStartEnd"
                    tickLine={false}
                  />
                  <YAxis allowDecimals={false} tickLine={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#0f766e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Correlation matrix"
          subtitle="Numerical variables only; correlation is not causation"
          className="wide-chart"
        >
          {correlationColumns.length < 2 ? (
            <EmptyState title="Not enough numerical columns">
              {correlation?.message ??
                "At least two numerical columns are required."}
            </EmptyState>
          ) : (
            <div className="correlation-scroll">
              <table className="correlation-table">
                <thead>
                  <tr>
                    <th></th>
                    {correlationColumns.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {correlationColumns.map((row) => (
                    <tr key={row}>
                      <th>{row}</th>
                      {correlationColumns.map((column) => {
                        const value = correlation.correlation?.[column]?.[row];
                        const strength = value == null ? 0 : Math.abs(value);
                        const shade = Math.min(strength, 1) * 0.42;
                        return (
                          <td
                            key={column}
                            style={{
                              backgroundColor:
                                value == null
                                  ? "transparent"
                                  : value >= 0
                                    ? `rgba(79, 70, 229, ${shade})`
                                    : `rgba(220, 38, 38, ${shade})`,
                            }}
                            title={`${row} × ${column}`}
                          >
                            {value == null ? "—" : Number(value).toFixed(2)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Column statistics"
          subtitle="Descriptive statistics returned for each dataset column"
          className="wide-chart"
        >
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Column</th>
                  {statisticsMetrics.map((metric) => (
                    <th key={metric}>{metric}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(columnStats?.stats ?? {}).map(
                  ([column, metrics]) => (
                    <tr key={column}>
                      <th>{column}</th>
                      {statisticsMetrics.map((metric) => {
                        const value = metrics[metric];
                        return (
                          <td key={metric}>
                            {value == null
                              ? "—"
                              : typeof value === "number"
                                ? Number(value.toFixed(3))
                                : value}
                          </td>
                        );
                      })}
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </ChartCard>

        <ChartCard
          title="Customer history versus spend"
          subtitle="A sample of up to 500 valid customer records"
          className="wide-chart"
          action={
            <div className="chart-selects">
              <label>
                X{" "}
                <select
                  className="select-control"
                  value={xColumn}
                  onChange={(event) => setXColumn(event.target.value)}
                >
                  {numericColumns.map((column) => (
                    <option key={column}>{column}</option>
                  ))}
                </select>
              </label>
              <label>
                Y{" "}
                <select
                  className="select-control"
                  value={yColumn}
                  onChange={(event) => setYColumn(event.target.value)}
                >
                  {numericColumns.map((column) => (
                    <option key={column}>{column}</option>
                  ))}
                </select>
              </label>
            </div>
          }
        >
          {scatterLoading ? (
            <LoadingSpinner />
          ) : scatterError ? (
            <ErrorMessage message={scatterError} />
          ) : !scatter?.data?.length ? (
            <EmptyState title="No valid points for these columns" />
          ) : (
            <div className="chart-frame">
              <ResponsiveContainer width="100%" height={320}>
                <ScatterChart
                  margin={{ top: 12, right: 16, bottom: 16, left: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={xColumn} type="number" name={xColumn} />
                  <YAxis dataKey={yColumn} type="number" name={yColumn} />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                  <Scatter data={scatter.data} fill="#4f46e5" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartCard>
      </div>

      <p className="causal-note">
        Exploratory analysis describes the dataset. Causal effects will be
        estimated in a later stage using an appropriate treatment definition and
        a validated modeling pipeline.
      </p>
      <p className="causal-note secondary-note">
        The Hillstrom dataset measures email marketing campaigns, not randomized
        discount amounts. Visit occurs after treatment and should not be treated
        as a pre-treatment feature when estimating the total effect on
        conversion.
      </p>
    </div>
  );
}

export default EDAPage;
