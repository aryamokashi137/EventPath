import api from "./api";

export const getProjects = async () => {
  const response = await api.get("/projects");
  return response.data;
};

export const createProject = async (projectData) => {
  const response = await api.post("/projects", projectData);
  return response.data;
};

export const getProject = async (projectId) => {
  const response = await api.get(`/projects/${projectId}`);
  return response.data;
};

export const updateProject = async (projectId, projectData) => {
  const response = await api.put(
    `/projects/${projectId}`,
    projectData
  );
  return response.data;
};

export const deleteProject = async (projectId) => {
  const response = await api.delete(
    `/projects/${projectId}`
  );
  return response.data;
};

export const getProjectNetwork = async (projectId) => {
  const response = await api.get(
    `/projects/${projectId}/network`
  );
  return response.data;
};

export const getProjectPERT = async (projectId) => {
  const response = await api.get(
    `/projects/${projectId}/pert`
  );
  return response.data;
};

export const simulateProject = async (
  projectId,
  simulationData
) => {
  const response = await api.post(
    `/projects/${projectId}/simulate`,
    simulationData
  );
  return response.data;
};

export const crashProject = async (
  projectId,
  crashData
) => {
  const response = await api.post(
    `/projects/${projectId}/crash`,
    crashData
  );
  return response.data;
};

export const runMonteCarlo = async (
  projectId,
  simulationData
) => {
  const response = await api.post(
    `/projects/${projectId}/monte-carlo`,
    simulationData
  );
  return response.data;
};