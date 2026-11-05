import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchDatasetDetails,
  fetchDatasetList,
  getActiveDatasetId,
  getApiErrorMessage,
  setActiveDatasetId,
  uploadDataset,
} from "../services/api";

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
const DEFAULT_FEATURES = [
  "recency",
  "history_segment",
  "history",
  "mens",
  "womens",
  "zip_code",
  "newbie",
  "channel",
];
const IGNORED_FEATURES = new Set([
  "id",
  "customer_id",
  "user_id",
  "visit",
  "visits",
  "conversion",
  "purchase",
  "revenue",
  "outcome",
]);

const preferredColumn = (columns, names) =>
  names.find((name) => columns.includes(name)) ?? "";

function CheckItem({ level, children }) {
  const styles = {
    ok: "border-emerald-200 bg-emerald-50 text-emerald-800",
    warn: "border-amber-200 bg-amber-50 text-amber-800",
    error: "border-rose-200 bg-rose-50 text-rose-800",
  };
  const labels = { ok: "Passed", warn: "Review", error: "Issue" };

  return (
    <li className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${styles[level]}`}>
      <span className="mt-0.5 rounded-md bg-white/70 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide">
        {labels[level]}
      </span>
      <span>{children}</span>
    </li>
  );
}

export default function DataWorkspace() {
  const [datasets, setDatasets] = useState([]);
  const [datasetId, setDatasetId] = useState(() => getActiveDatasetId() ?? "");
  const [details, setDetails] = useState(null);
  const [file, setFile] = useState(null);
  const [roles, setRoles] = useState({ treatment: "", outcome: "", features: [] });
  const [validation, setValidation] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(
    () => Boolean(getActiveDatasetId()),
  );
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const columns = details?.columns ?? [];
  const isHillstromCompatible = details?.causal_compatibility?.compatible ?? false;

  useEffect(() => {
    let active = true;
    fetchDatasetList()
      .then(({ datasets: available }) => {
        if (active) setDatasets(available);
      })
      .catch((requestError) => {
        if (active) setError(getApiErrorMessage(requestError));
      })
      .finally(() => {
        if (active) setLoadingList(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const syncSelection = () => {
      const nextId = getActiveDatasetId() ?? "";
      setDatasetId(nextId);
      setDetails(null);
      setValidation(null);
      setLoadingDetails(Boolean(nextId));
    };
    window.addEventListener("storage", syncSelection);
    window.addEventListener("econocausal:activeDatasetChanged", syncSelection);
    return () => {
      window.removeEventListener("storage", syncSelection);
      window.removeEventListener("econocausal:activeDatasetChanged", syncSelection);
    };
  }, []);

  useEffect(() => {
    if (!datasetId) return undefined;

    let active = true;
    fetchDatasetDetails(datasetId)
      .then((result) => {
        if (!active) return;
        setDetails(result);
        const availableColumns = result.columns;
        const treatment = preferredColumn(availableColumns, [
          "segment",
          "treatment",
          "treated",
        ]);
        const outcome = preferredColumn(availableColumns, [
          "conversion",
          "outcome",
          "purchase",
        ]);
        const recommendedFeatures = DEFAULT_FEATURES.filter(
          (column) =>
            availableColumns.includes(column) &&
            column !== treatment &&
            column !== outcome,
        );
        const otherFeatures = availableColumns.filter(
          (column) =>
            !IGNORED_FEATURES.has(column.toLowerCase()) &&
            column !== treatment &&
            column !== outcome,
        );
        setRoles({
          treatment,
          outcome,
          features: recommendedFeatures.length ? recommendedFeatures : otherFeatures,
        });
        setError("");
      })
      .catch((requestError) => {
        if (active) setError(getApiErrorMessage(requestError));
      })
      .finally(() => {
        if (active) setLoadingDetails(false);
      });

    return () => {
      active = false;
    };
  }, [datasetId]);

  const selectDataset = (nextId) => {
    setDatasetId(nextId);
    setActiveDatasetId(nextId);
    setDetails(null);
    setValidation(null);
    setLoadingDetails(Boolean(nextId));
    setError("");
  };

  const handleUpload = async () => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Only CSV files are accepted.");
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setError("The file is larger than the 20 MB upload limit.");
      return;
    }

    setUploading(true);
    setError("");
    try {
      const uploaded = await uploadDataset(file);
      setDatasetId(uploaded.dataset_id);
      setLoadingDetails(true);
      setFile(null);
      const { datasets: available } = await fetchDatasetList();
      setDatasets(available);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setUploading(false);
    }
  };

  const updateRole = (change) => {
    setRoles((current) => {
      const next = { ...current, ...change };
      next.features = next.features.filter(
        (column) => column !== next.treatment && column !== next.outcome,
      );
      return next;
    });
    setValidation(null);
  };

  const toggleFeature = (column) => {
    setRoles((current) => ({
      ...current,
      features: current.features.includes(column)
        ? current.features.filter((feature) => feature !== column)
        : [...current.features, column],
    }));
    setValidation(null);
  };

  const validateRoles = () => {
    const checks = [];
    const missing = [
      roles.treatment,
      roles.outcome,
      ...roles.features,
    ].filter((column) => column && !columns.includes(column));
    const validRoles = Boolean(
      roles.treatment &&
        roles.outcome &&
        roles.treatment !== roles.outcome &&
        roles.features.length > 0 &&
        missing.length === 0,
    );

    if (!roles.treatment || !roles.outcome) {
      checks.push({ level: "error", text: "Choose both a treatment column and an outcome column." });
    } else if (roles.treatment === roles.outcome) {
      checks.push({ level: "error", text: "Treatment and outcome must be different columns." });
    } else {
      checks.push({ level: "ok", text: "Treatment and outcome are selected as separate columns." });
    }

    if (!roles.features.length) {
      checks.push({ level: "error", text: "Select at least one customer feature." });
    } else if (missing.length) {
      checks.push({ level: "error", text: `Selected columns are missing: ${missing.join(", ")}.` });
    } else {
      checks.push({ level: "ok", text: `${roles.features.length} customer feature(s) are present in this dataset.` });
    }

    if (isHillstromCompatible) {
      checks.push({ level: "ok", text: "Dataset has the required Hillstrom columns for the current causal workflow." });
    } else {
      const missingColumns = details?.causal_compatibility?.missing_columns ?? [];
      checks.push({
        level: "warn",
        text: `Dataset exploration is available, but the current causal model requires Hillstrom columns${missingColumns.length ? `: ${missingColumns.join(", ")}` : "."}`,
      });
    }

    setValidation({ checks, rolesValid: validRoles });
  };

  return (
    <div className="space-y-8">
      <section>
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
          CAMPAIGN DATA
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-[34px]">
          Start with your data
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 sm:text-[15px]">
          Upload campaign history, inspect its columns, and validate treatment, outcome, and customer feature selections.
        </p>
      </section>

      <nav className="flex flex-wrap gap-2" aria-label="Data workspace views">
        <Link className="rounded-lg bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700" to="/upload">
          Workspace
        </Link>
        <Link className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-white" to="/eda">
          Exploratory analysis
        </Link>
        <Link className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-white" to="/preview">
          Dataset preview
        </Link>
      </nav>

      {error && (
        <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      )}

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(280px,0.8fr)]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Import campaign history</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              Choose a CSV with one row per customer and their campaign outcome.
            </p>
          </div>
          <label
            htmlFor="campaign-file"
            className="mt-6 flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/70 p-5 text-center hover:bg-slate-50"
          >
            <span className="text-sm font-semibold text-slate-800">
              {file ? file.name : "Choose a CSV file to upload"}
            </span>
            <span className="mt-1 text-xs text-slate-500">CSV format · Maximum 20 MB</span>
            <input
              id="campaign-file"
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <button
            className="mt-4 inline-flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            disabled={!file || uploading}
            onClick={handleUpload}
          >
            {uploading ? "Uploading…" : "Upload dataset"}
          </button>
        </div>

        <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-sm font-semibold text-slate-900">Select a dataset</h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Choose the upload used by exploration and causal analysis.
          </p>
          <select
            aria-label="Selected dataset"
            className="mt-5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"
            value={datasetId}
            disabled={loadingList}
            onChange={(event) => selectDataset(event.target.value)}
          >
            <option value="">
              {loadingList ? "Loading datasets…" : "Select a dataset"}
            </option>
            {datasets.map((dataset) => (
              <option key={dataset.dataset_id} value={dataset.dataset_id}>
                {dataset.filename}
              </option>
            ))}
          </select>
          {!loadingList && !datasets.length && (
            <p className="mt-3 text-xs text-slate-500">No uploaded datasets found yet.</p>
          )}
          {details && (
            <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-slate-500">Rows</div>
                <strong className="mt-1 block text-sm text-slate-900">{details.rows.toLocaleString()}</strong>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-slate-500">Columns</div>
                <strong className="mt-1 block text-sm text-slate-900">{details.columns.length}</strong>
              </div>
            </div>
          )}
        </aside>
      </section>

      {loadingDetails && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Loading selected dataset…
        </div>
      )}

      {details && !loadingDetails && (
        <>
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Review dataset roles</h2>
                <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
                  Select columns for a data-quality check. This selector does not change the fixed Hillstrom treatment, outcome, or model features used in Weeks 1–3.
                </p>
              </div>
              <span className={`self-start rounded-full px-3 py-1 text-xs font-semibold ${isHillstromCompatible ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                {isHillstromCompatible ? "Hillstrom compatible" : "Exploration only"}
              </span>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {[
                { key: "treatment", label: "Treatment", help: "What the customer received" },
                { key: "outcome", label: "Outcome", help: "What happened after the campaign" },
              ].map(({ key, label, help }) => (
                <label key={key} className="text-sm font-medium text-slate-700">
                  {label}
                  <span className="mt-1 block text-xs font-normal text-slate-500">{help}</span>
                  <select
                    className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"
                    value={roles[key]}
                    onChange={(event) => updateRole({ [key]: event.target.value })}
                  >
                    <option value="">Select a column…</option>
                    {columns.map((column) => (
                      <option key={column} value={column}>{column}</option>
                    ))}
                  </select>
                </label>
              ))}
            </div>

            <div className="mt-6">
              <div className="text-sm font-medium text-slate-800">Customer features</div>
              <p className="mt-1 text-xs text-slate-500">
                Select customer facts known before treatment. Treatment and outcome columns are excluded.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {columns
                  .filter(
                    (column) =>
                      column !== roles.treatment &&
                      column !== roles.outcome &&
                      !IGNORED_FEATURES.has(column.toLowerCase()),
                  )
                  .map((column) => {
                    const selected = roles.features.includes(column);
                    return (
                      <label
                        key={column}
                        className={`cursor-pointer rounded-lg border px-3 py-2 text-sm transition ${
                          selected
                            ? "border-indigo-200 bg-indigo-50 font-medium text-indigo-700"
                            : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="sr-only"
                          checked={selected}
                          onChange={() => toggleFeature(column)}
                        />
                        <span className="mr-2 inline-flex h-4 w-4 align-[-3px] items-center justify-center rounded border border-current text-[10px]">
                          {selected ? "✓" : ""}
                        </span>
                        {column}
                      </label>
                    );
                  })}
              </div>
            </div>

            <button
              className="mt-7 inline-flex items-center justify-center rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
              type="button"
              onClick={validateRoles}
            >
              Validate dataset
            </button>
          </section>

          {validation && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
              <h2 className="font-semibold text-slate-900">Data quality check</h2>
              <p className="mt-1 text-sm text-slate-500">
                Review column selection and model compatibility before continuing.
              </p>
              <ul className="mt-5 space-y-2">
                {validation.checks.map((check, index) => (
                  <CheckItem key={`${check.level}-${index}`} level={check.level}>
                    {check.text}
                  </CheckItem>
                ))}
              </ul>
              <div className="mt-5 flex flex-wrap gap-3">
                {validation.rolesValid && isHillstromCompatible ? (
                  <Link
                    className="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
                    to="/uplift"
                  >
                    Continue to uplift analysis →
                  </Link>
                ) : (
                  <Link
                    className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    to="/eda"
                  >
                    Explore this dataset
                  </Link>
                )}
              </div>
            </section>
          )}

          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 px-5 py-4">
              <h2 className="text-sm font-semibold text-slate-900">Dataset preview</h2>
              <p className="mt-1 text-xs text-slate-500">
                {details.filename} · {details.missing_values.toLocaleString()} missing values
              </p>
            </div>
            <div className="max-h-[420px] overflow-auto">
              <table className="min-w-full divide-y divide-slate-100 text-left text-sm">
                <thead className="sticky top-0 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <tr>
                    {columns.map((column) => (
                      <th className="whitespace-nowrap px-4 py-3" key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {details.preview.map((row, index) => (
                    <tr key={`${datasetId}-${index}`} className="hover:bg-slate-50">
                      {columns.map((column) => (
                        <td className="whitespace-nowrap px-4 py-3 text-slate-600" key={column}>
                          {row[column] == null ? "—" : String(row[column])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
