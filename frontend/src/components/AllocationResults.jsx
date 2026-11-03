import { useEffect, useMemo, useState } from "react";
import {
  downloadAllocationCsv,
  fetchAllocationResult,
  getApiErrorMessage,
  optimizeCustomerAllocation,
} from "../services/api";
import { ErrorMessage, LoadingSpinner } from "./Feedback";

const PAGE_SIZE = 25;
const CAMPAIGN_BUDGET_KEY = "econocausal:campaignBudget";

const formatMoney = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);

export default function AllocationResults({ datasetId }) {
  const [budget, setBudget] = useState(
    () => window.localStorage.getItem(CAMPAIGN_BUDGET_KEY) ?? "",
  );
  const [interventionCost, setInterventionCost] = useState("");
  const [maxCustomers, setMaxCustomers] = useState("");
  const [allocation, setAllocation] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [selectedOnly, setSelectedOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [segment, setSegment] = useState("");
  const [sortBy, setSortBy] = useState("predicted_ite");
  const [sortDirection, setSortDirection] = useState("desc");
  const [optimizing, setOptimizing] = useState(false);
  const [loadedRowsKey, setLoadedRowsKey] = useState(null);
  const [error, setError] = useState(null);

  const allocationId = allocation?.allocation_id;
  const rowsRequestKey = JSON.stringify([
    allocationId,
    offset,
    selectedOnly,
    query,
    segment,
    sortBy,
    sortDirection,
  ]);
  const loadingRows = Boolean(allocationId && loadedRowsKey !== rowsRequestKey);
  const numericBudget = Number(budget);
  const numericCost = Number(interventionCost);
  const numericMaxCustomers = maxCustomers === "" ? null : Number(maxCustomers);
  const canOptimize =
    Number.isFinite(numericBudget) &&
    numericBudget > 0 &&
    Number.isFinite(numericCost) &&
    numericCost > 0 &&
    (numericMaxCustomers === null ||
      (Number.isInteger(numericMaxCustomers) && numericMaxCustomers >= 0));
  const page = Math.floor(offset / PAGE_SIZE);
  const pageCount = Math.ceil(total / PAGE_SIZE);

  useEffect(() => {
    if (!allocationId) return undefined;
    let active = true;
    fetchAllocationResult(allocationId, {
      offset,
      limit: PAGE_SIZE,
      selected_only: selectedOnly,
      query: query.trim() || undefined,
      segment: segment || undefined,
      sort_by: sortBy,
      sort_direction: sortDirection,
    })
      .then((result) => {
        if (!active) return;
        setCustomers(result.customers);
        setTotal(result.total_customers);
      })
      .catch((requestError) => {
        if (active) setError(getApiErrorMessage(requestError));
      })
      .finally(() => {
        if (active) setLoadedRowsKey(rowsRequestKey);
      });
    return () => {
      active = false;
    };
  }, [
    allocationId,
    offset,
    selectedOnly,
    query,
    segment,
    sortBy,
    sortDirection,
    rowsRequestKey,
  ]);

  const runOptimization = async (event) => {
    event.preventDefault();
    setError(null);
    setOptimizing(true);
    setAllocation(null);
    setCustomers([]);
    setOffset(0);
    try {
      const result = await optimizeCustomerAllocation({
        dataset_id: datasetId,
        budget: numericBudget,
        intervention_cost: numericCost,
        max_customers: numericMaxCustomers,
        segment_column: "history_segment",
      });
      setAllocation(result);
      setTotal(result.total_customers);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setOptimizing(false);
    }
  };

  const toggleSort = (column) => {
    setOffset(0);
    if (sortBy === column) {
      setSortDirection((direction) => (direction === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(column);
      setSortDirection(
        column === "customer_id" || column === "segment" ? "asc" : "desc",
      );
    }
  };

  const segmentSummaries = useMemo(
    () => allocation?.summary?.segment_summaries ?? [],
    [allocation],
  );

  const exportCsv = async () => {
    try {
      const csv = await downloadAllocationCsv(allocation.allocation_id);
      const url = URL.createObjectURL(csv);
      const link = document.createElement("a");
      link.href = url;
      link.download = `econocausal-allocation-${allocation.allocation_id}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  };

  return (
    <section className="panel causal-section allocation-section">
      <div className="panel-heading">
        <div>
          <h2>Week 3 · Personalized allocation</h2>
          <p>
            Select email interventions that maximize estimated incremental
            conversions within the configured budget.
          </p>
        </div>
      </div>
      <form className="allocation-config" onSubmit={runOptimization}>
        <label>
          Total budget (USD)
          <input
            aria-label="Total budget"
            type="number"
            min="0.01"
            step="0.01"
            value={budget}
            onChange={(event) => {
              const value = event.target.value;
              setBudget(value);
              if (value !== "" && Number.isFinite(Number(value)) && Number(value) > 0) {
                window.localStorage.setItem(CAMPAIGN_BUDGET_KEY, value);
              } else {
                window.localStorage.removeItem(CAMPAIGN_BUDGET_KEY);
              }
            }}
            required
          />
        </label>
        <label>
          Cost per intervention (USD)
          <input
            aria-label="Cost per intervention"
            type="number"
            min="0.01"
            step="0.01"
            value={interventionCost}
            onChange={(event) => setInterventionCost(event.target.value)}
            required
          />
        </label>
        <label>
          Maximum customers (optional)
          <input
            aria-label="Maximum customers"
            type="number"
            min="0"
            step="1"
            value={maxCustomers}
            onChange={(event) => setMaxCustomers(event.target.value)}
          />
        </label>
        <button
          className="button button-primary"
          type="submit"
          disabled={!canOptimize || optimizing}
        >
          {optimizing ? "Optimizing…" : "Optimize allocation"}
        </button>
      </form>
      <p className="causal-note">
        This objective is incremental conversions, not profit. The Hillstrom
        model estimates Womens E-Mail versus No E-Mail and does not estimate
        discount effects or customer revenue.
      </p>
      {optimizing && <LoadingSpinner label="Solving the binary allocation problem…" />}
      {error && <ErrorMessage message={error} />}

      {allocation && (
        <>
          <div className="allocation-summary">
            <div><span>Available budget</span><strong>{formatMoney(allocation.summary.budget)}</strong></div>
            <div><span>Allocated budget</span><strong>{formatMoney(allocation.summary.allocated_budget)}</strong></div>
            <div><span>Remaining budget</span><strong>{formatMoney(allocation.summary.remaining_budget)}</strong></div>
            <div><span>Selected customers</span><strong>{allocation.summary.customers_selected.toLocaleString()}</strong></div>
            <div><span>Expected incremental conversions</span><strong>{allocation.summary.expected_incremental_conversions.toFixed(3)}</strong></div>
            <div><span>Average selected uplift</span><strong>{(allocation.summary.average_selected_uplift * 100).toFixed(2)} pp</strong></div>
          </div>
          <p className="causal-note">
            Customers evaluated: {allocation.summary.customers_evaluated.toLocaleString()}.
            {" "}Estimated profit is not reported because reliable revenue inputs were not supplied.
          </p>

          {segmentSummaries.length > 0 && (
            <div className="table-scroll">
              <h3>Segment allocation summary</h3>
              <table className="data-table">
                <thead>
                  <tr><th>Segment</th><th>Evaluated</th><th>Selected</th><th>Allocated budget</th><th>Expected incremental conversions</th></tr>
                </thead>
                <tbody>
                  {segmentSummaries.map((item) => (
                    <tr key={item.segment}>
                      <td>{item.segment}</td>
                      <td>{item.customers_evaluated.toLocaleString()}</td>
                      <td>{item.customers_selected.toLocaleString()}</td>
                      <td>{formatMoney(item.allocated_budget)}</td>
                      <td>{item.expected_incremental_conversions.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="allocation-table-controls">
            <label>
              Filter customer ID
              <input
                aria-label="Filter customer ID"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setOffset(0);
                }}
              />
            </label>
            {segmentSummaries.length > 0 && (
              <label>
                Segment
                <select
                  aria-label="Filter segment"
                  value={segment}
                  onChange={(event) => {
                    setSegment(event.target.value);
                    setOffset(0);
                  }}
                >
                  <option value="">All segments</option>
                  {segmentSummaries.map((item) => (
                    <option key={item.segment} value={item.segment}>{item.segment}</option>
                  ))}
                </select>
              </label>
            )}
            <label className="allocation-selected-filter">
              <input
                type="checkbox"
                checked={selectedOnly}
                onChange={(event) => {
                  setSelectedOnly(event.target.checked);
                  setOffset(0);
                }}
              />
              Selected only
            </label>
            <button className="button button-secondary" type="button" onClick={exportCsv}>
              Export CSV
            </button>
          </div>

          {loadingRows ? (
            <LoadingSpinner label="Loading allocation rows…" />
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th><button type="button" onClick={() => toggleSort("customer_id")}>Customer ID</button></th>
                    <th><button type="button" onClick={() => toggleSort("segment")}>Segment</button></th>
                    <th><button type="button" onClick={() => toggleSort("predicted_ite")}>Predicted ITE</button></th>
                    <th><button type="button" onClick={() => toggleSort("expected_incremental_benefit")}>Expected incremental benefit</button></th>
                    <th><button type="button" onClick={() => toggleSort("intervention_cost")}>Intervention cost</button></th>
                    <th><button type="button" onClick={() => toggleSort("selected")}>Selected</button></th>
                    <th>Allocation reason</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((customer) => (
                    <tr key={customer.customer_id}>
                      <td>{customer.customer_id}</td>
                      <td>{customer.segment ?? "—"}</td>
                      <td>{Number(customer.predicted_ite).toFixed(5)}</td>
                      <td>{Number(customer.expected_incremental_benefit).toFixed(5)}</td>
                      <td>{formatMoney(customer.intervention_cost)}</td>
                      <td>{customer.selected ? "Yes" : "No"}</td>
                      <td>{customer.allocation_reason}</td>
                    </tr>
                  ))}
                  {!customers.length && (
                    <tr><td colSpan="7">No customers match these filters.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
          <div className="causal-pagination">
            <span>{total.toLocaleString()} customers · Page {pageCount ? page + 1 : 0} of {pageCount}</span>
            <div>
              <button
                className="button button-secondary"
                type="button"
                onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
                disabled={offset === 0}
              >
                Previous
              </button>
              <button
                className="button button-secondary"
                type="button"
                onClick={() => setOffset((current) => current + PAGE_SIZE)}
                disabled={page >= pageCount - 1}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
