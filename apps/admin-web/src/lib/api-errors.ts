import axios from "axios";

import type { ApiErrorResponse } from "@/features/auth/types";

export function describeApiFailure(error: unknown) {
  if (!axios.isAxiosError(error))
    return { message: "This request failed. Please try again." };
  const status = error.response?.status;
  const requestId = error.response?.headers?.["x-request-id"] as string | undefined;
  const message =
    error.code === "ECONNABORTED" || error.code === "ETIMEDOUT"
      ? "The server took too long to respond. Please try again."
      : axios.isCancel(error)
        ? "The request was interrupted. Please try again."
        : status === 401
          ? "Your session has expired. Please sign in again."
          : status === 403
            ? "You do not have permission to view this content."
            : status && status >= 500
              ? "The server could not complete this request. Please try again shortly."
              : !error.response
                ? "The API cannot be reached. Check your connection and SSH tunnel."
                : getApiErrorDetail(error);
  return { message, status, requestId };
}

export function getApiErrorDetail(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  if (!axios.isAxiosError<ApiErrorResponse>(error)) {
    return fallback;
  }
  const detail = error.response?.data.detail;
  return typeof detail === "string" ? detail : fallback;
}
