import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AllocationResults from "../components/AllocationResults";
import { ErrorMessage, LoadingSpinner } from "../components/Feedback";
import {
  fetchModelInfo,
  getActiveDatasetId,
  getApiErrorMessage,
} from "../services/api";

export default function AllocationPage() {
  const [datasetId, setDatasetId] = useState(getActiveDatasetId);
  const [modelInfo, setModelInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [modelMissing, setModelMissing] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const updateDataset = () => {
      setDatasetId(getActiveDatasetId());
      setModelInfo(null);
      setModelMissing(false);
      setError(null);
      setLoading(true);
    };
    window.addEventListener("storage", updateDataset);
    window.addEventListener("econocausal:activeDatasetChanged", updateDataset);
    return () => {
      window.removeEventListener("storage", updateDataset);
      window.removeEventListener("econocausal:activeDatasetChanged", updateDataset);
    };
  }, []);

  useEffect(() => {
    let active = true;
    fetchModelInfo()
      .then((info) => {
        if (active) setModelInfo(info);
      })
      .catch((requestError) => {
        if (!active) return;
        if (requestError.response?.status === 503) {
          setModelMissing(true);
          setModelInfo(null);
        } else {
          setError(getApiErrorMessage(requestError));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [datasetId]);

  const modelMatchesDataset =
    Boolean(datasetId) && Boolean(modelInfo?.metadata_available) &&
    modelInfo.dataset_id === datasetId;

  return (
    <div className="space-y-8">
      <section>
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-violet-100 bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700">
          <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
          WEEK 3 · BUDGET PLANNING
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-[34px]">
          Optimize your allocation
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 sm:text-[15px]">
          Set a campaign budget and intervention cost to target customers with the highest estimated incremental conversion effect.
        </p>
      </section>

      {loading && <LoadingSpinner label="Checking the trained model…" />}
      {error && <ErrorMessage message={error} />}

      {!loading && !datasetId && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-slate-900">Select a dataset first</h2>
          <p className="mt-1 text-sm text-slate-600">
            Upload or select a Hillstrom-compatible dataset in the Data workspace.
          </p>
          <Link className="mt-4 inline-flex rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700" to="/upload">
            Open data workspace
          </Link>
        </section>
      )}

      {!loading && datasetId && modelMissing && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
          No trained model is available yet. Train the causal model in Uplift Analysis before creating a budget allocation.
          <div>
            <Link className="mt-4 inline-flex rounded-lg bg-indigo-600 px-4 py-2.5 font-semibold text-white hover:bg-indigo-700" to="/uplift">
              Go to uplift analysis
            </Link>
          </div>
        </section>
      )}

      {!loading && datasetId && modelInfo && !modelMatchesDataset && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
          {modelInfo.metadata_available
            ? "The latest model was trained on a different dataset. Retrain on the selected dataset before allocation."
            : "The saved model has no dataset compatibility metadata. Retrain it before allocation."}
          <div>
            <Link className="mt-4 inline-flex rounded-lg bg-indigo-600 px-4 py-2.5 font-semibold text-white hover:bg-indigo-700" to="/uplift">
              Train for this dataset
            </Link>
          </div>
        </section>
      )}

      {!loading && modelMatchesDataset && (
        <>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            Model ready · {modelInfo.model_class} · run {modelInfo.model_id} · trained for the selected dataset.
            <div className="mt-1 text-xs">
              Treatment: {modelInfo.treatment_definition ?? "Womens E-Mail vs No E-Mail"} · Outcome: {modelInfo.outcome ?? "conversion"}
            </div>
          </div>
          <AllocationResults key={datasetId} datasetId={datasetId} />
        </>
      )}

    </div>
  );
}
