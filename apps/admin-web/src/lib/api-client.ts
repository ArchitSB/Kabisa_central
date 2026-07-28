import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import { apiBaseUrl } from "@/features/auth/auth-client";
import { refreshAccessToken, useAuthStore } from "@/features/auth/auth-store";

type RetryableRequest = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10_000,
});

apiClient.interceptors.request.use((config) => {
  const accessToken = useAuthStore.getState().accessToken;
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as RetryableRequest | undefined;
    if (error.response?.status !== 401 || !request || request._retry) {
      return Promise.reject(error);
    }

    request._retry = true;
    const accessToken = await refreshAccessToken();
    if (accessToken) {
      request.headers.Authorization = `Bearer ${accessToken}`;
      return apiClient(request);
    }

    useAuthStore.getState().clearSession();
    if (window.location.pathname !== "/login") {
      const returnTo = `${window.location.pathname}${window.location.search}`;
      window.location.assign(`/login?returnTo=${encodeURIComponent(returnTo)}`);
    }
    return Promise.reject(error);
  },
);
