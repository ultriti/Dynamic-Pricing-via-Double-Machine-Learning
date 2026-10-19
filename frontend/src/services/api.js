import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 20000,
});

export const getApiErrorMessage = (error) => {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) {
    const missing = detail.missing_columns?.join(", ");
    return missing ? `${detail.message} Missing: ${missing}.` : detail.message;
  }
  return error.message || "The request could not be completed.";
};

export const checkApiHealth = async () => (await api.get("/api/health")).data;

export const uploadDataset = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/api/dataset/upload", formData);
  return data;
};

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

export const fetchModelPredictions = async () =>
  (await api.get("/api/model/ite")).data;
