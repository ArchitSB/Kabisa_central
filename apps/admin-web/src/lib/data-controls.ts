import { apiClient } from "@/lib/api-client";

export type BulkActionResult = {
  action: string;
  applied: number;
  skipped: number;
  failed: number;
  results: Array<{
    id: string;
    status: "applied" | "skipped" | "failed";
    detail: string | null;
  }>;
};

export type ExportParams = Record<string, string | number | boolean | string[] | undefined>;

export async function runBulkAction(
  path: string,
  payload: { ids: string[]; action: string; value?: string; note?: string },
) {
  const response = await apiClient.post<BulkActionResult>(path, payload);
  return response.data;
}

export async function downloadSection(
  path: string,
  params: ExportParams,
  filename: string,
) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === "") return;
    if (Array.isArray(value)) value.forEach((item) => query.append(key, item));
    else query.append(key, String(value));
  });
  const response = await apiClient.get<Blob>(path, {
    params: query,
    responseType: "blob",
    timeout: 60_000,
  });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function bulkResultMessage(result: BulkActionResult): {
  title: string;
  description?: string;
} {
  const title = `${result.applied} applied${result.skipped ? `, ${result.skipped} skipped` : ""}${result.failed ? `, ${result.failed} failed` : ""}`;
  const details = result.results
    .filter((item) => item.status !== "applied" && item.detail)
    .slice(0, 2)
    .map((item) => item.detail)
    .join(" ");
  return { title, description: details || undefined };
}
