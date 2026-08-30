import api from "./api";

export const createActivity = async (
  projectId,
  activityData
) => {
  const response = await api.post(
    `/projects/${projectId}/activities`,
    activityData
  );

  return response.data;
};

export const updateActivity = async (
  projectId,
  activityId,
  activityData
) => {
  const response = await api.put(
    `/projects/${projectId}/activities/${activityId}`,
    activityData
  );

  return response.data;
};

export const deleteActivity = async (
  projectId,
  activityId
) => {
  await api.delete(
    `/projects/${projectId}/activities/${activityId}`
  );
};