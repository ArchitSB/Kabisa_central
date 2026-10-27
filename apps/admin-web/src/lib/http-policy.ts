import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS);
export const apiTimeoutMs =
  Number.isFinite(configuredTimeout) && configuredTimeout > 0 ? configuredTimeout : 10_000;

type ReadRequest = InternalAxiosRequestConfig & { _readRetry?: boolean };

export function isTransientReadError(error: unknown): boolean {
  if (!axios.isAxiosError(error) || axios.isCancel(error)) return false;
  return (
    error.config?.method?.toLowerCase() === "get" &&
    (error.code === "ECONNABORTED" ||
      error.code === "ETIMEDOUT" ||
      error.code === "ERR_NETWORK" ||
      [502, 503, 504].includes(error.response?.status ?? 0))
  );
}

export function installReadRetry(client: AxiosInstance) {
  client.interceptors.response.use(undefined, async (error: unknown) => {
    if (isTransientReadError(error) && axios.isAxiosError(error)) {
      const config = error.config as ReadRequest;
      if (!config._readRetry) {
        config._readRetry = true;
        await new Promise((resolve) => setTimeout(resolve, 1500));
        if (!config.signal?.aborted) return client.request(config);
      }
    }
    throw error;
  });
}
