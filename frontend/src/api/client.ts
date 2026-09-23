import axios from "axios";

import { tokenStorage } from "../auth/tokenStorage";

// Same-origin by default: nginx (see nginx.conf) proxies /api, /docs, etc.
// to the backend container, so the browser never needs a separate port.
// Only set VITE_API_BASE_URL if the API is genuinely on a different origin.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    Accept: "application/json",
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = tokenStorage.get();

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      tokenStorage.remove();

      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  },
);
