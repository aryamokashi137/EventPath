import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// Intercept all outgoing HTTP requests to append the active user role header
api.interceptors.request.use((config) => {
  const role = localStorage.getItem("eventpath_user_role") || "ADMIN";
  config.headers["X-User-Role"] = role;
  return config;
});

export default api;