import api from "./api";

/**
 * Explainable AI explanation layer.
 *
 * Every endpoint returns the same report envelope, so the UI can render any
 * report with a single component: `report_type`, `title`, `headline`,
 * `summary`, `narrative`, `cards`, `metrics`, `evidence_trace` and
 * `confidence`.
 */

export const getCriticalPathExplanation = async (projectId) => {
  const response = await api.get(
    `/projects/${projectId}/xai/critical-path-explanation`
  );
  return response.data;
};

export const getRiskDiagnostics = async (projectId, params = {}) => {
  const response = await api.post(
    `/projects/${projectId}/xai/risk-diagnostics`,
    params
  );
  return response.data;
};

export const getCounterfactualCrashing = async (projectId, params = {}) => {
  const response = await api.post(
    `/projects/${projectId}/xai/counterfactual-crashing`,
    params
  );
  return response.data;
};

export const getVendorRecommendations = async (projectId) => {
  const response = await api.get(
    `/projects/${projectId}/xai/vendor-recommendations`
  );
  return response.data;
};

export const getXaiBundle = async (projectId) => {
  const response = await api.get(`/projects/${projectId}/xai/bundle`);
  return response.data;
};

export default {
  getCriticalPathExplanation,
  getRiskDiagnostics,
  getCounterfactualCrashing,
  getVendorRecommendations,
  getXaiBundle,
};
