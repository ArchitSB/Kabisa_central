import axios from "axios";

import type { ApiErrorResponse } from "@/features/auth/types";

export function getApiErrorDetail(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  if (!axios.isAxiosError<ApiErrorResponse>(error)) {
    return fallback;
  }
  return error.response?.data.detail ?? fallback;
}
