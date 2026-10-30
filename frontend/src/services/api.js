import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 180000,
});

const ACTIVE_DATASET_KEY = "econocausal:activeDatasetId";

export const getActiveDatasetId = () =>
  window.localStorage.getItem(ACTIVE_DATASET_KEY);

export const setActiveDatasetId = (datasetId) => {
  if (datasetId) {
    window.localStorage.setItem(ACTIVE_DATASET_KEY, datasetId);
  } else {
    window.localStorage.removeItem(ACTIVE_DATASET_KEY);
  }
};

api.interceptors.request.use((config) => {
  const datasetScoped =
    (config.method === "get" &&
      ((config.url?.startsWith("/api/dataset/") &&
        config.url !== "/api/dataset/list") ||
        config.url === "/api/causal/identify" ||
        config.url === "/api/model/ite" ||
        config.url === "/api/model/uplift-data")) ||
    (config.method === "post" && config.url === "/api/causal/train");
  const datasetId = window.localStorage.getItem(ACTIVE_DATASET_KEY);

  if (datasetScoped && datasetId) {
    config.params = { ...config.params, dataset_id: datasetId };
  }
  return config;
});

export const getApiErrorMessage = (error) => {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) {
    const missing = (
      detail.missing_columns ??
      detail.missing_features ??
      detail.missing
    )?.join(", ");
    return missing ? `${detail.message} Missing: ${missing}.` : detail.message;
  }
  const missing = detail?.missing_columns ?? detail?.missing_features;
  if (missing?.length) return `Missing required columns: ${missing.join(", ")}.`;
  return error.message || "The request could not be completed.";
};

export const checkApiHealth = async () => (await api.get("/api/health")).data;

export const uploadDataset = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/api/dataset/upload", formData);
  setActiveDatasetId(data.dataset_id);
  return data;
};

export const fetchDatasetList = async () =>
  (await api.get("/api/dataset/list")).data;

export const fetchCausalDag = async () =>
  (await api.get("/api/causal/dag")).data;

export const identifyCausalEffect = async () =>
  (await api.get("/api/causal/identify")).data;

export const trainCausalModel = async () =>
  (await api.post("/api/causal/train")).data;

export const fetchDatasetPreview = async () =>
  (await api.get("/api/dataset/preview")).data;

export const fetchDatasetSummary = async () =>
  (await api.get("/api/dataset/summary")).data;

export const fetchColumnStatistics = async () =>
  (await api.get("/api/dataset/columns")).data;

export const fetchValueCounts = async (column) =>
  (await api.get(`/api/dataset/value-counts/${encodeURIComponent(column)}`)).data;

export const fetchColumnDistribution = async (column) =>
  (
    await api.get(
      `/api/dataset/distribution/${encodeURIComponent(column)}`,
    )
  ).data;

export const fetchCorrelationMatrix = async () =>
  (await api.get("/api/dataset/correlation")).data;

export const fetchScatterPlot = async (x, y, sample = 500) =>
  (
    await api.get("/api/dataset/scatter", {
      params: { x, y, sample },
    })
  ).data;

export const fetchModelStatus = async () =>
  (await api.get("/api/model/status")).data;

export const fetchModelInfo = async () =>
  (await api.get("/api/model/info")).data;

export const fetchModelPredictions = async () =>
  (await api.get("/api/model/ite")).data;

export const fetchUpliftData = async () =>
  (await api.get("/api/model/uplift-data")).data;

