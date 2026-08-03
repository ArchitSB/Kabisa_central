import type {
  DashboardSummary,
  InventoryReport,
  ProductsReport,
  ReceivablesReport,
  ReportOptions,
  SalesReport,
} from "@/features/reporting/types";
import { apiClient } from "@/lib/api-client";

export type ReportKind = "sales" | "products" | "receivables" | "inventory";
export type ReportFilters = Record<string, string | number | undefined>;

export async function getDashboardSummary(warehouseId?: string) {
  const response = await apiClient.get<DashboardSummary>("/dashboard/summary", {
    params: { warehouse_id: warehouseId || undefined },
  });
  return response.data;
}
export async function getReportOptions() {
  const response = await apiClient.get<ReportOptions>("/reports/options");
  return response.data;
}
export async function getSalesReport(filters: ReportFilters) {
  const response = await apiClient.get<SalesReport>("/reports/sales", {
    params: { page: 1, page_size: 20, ...filters },
  });
  return response.data;
}
export async function getProductsReport(filters: ReportFilters) {
  const response = await apiClient.get<ProductsReport>("/reports/products", {
    params: { page: 1, page_size: 20, ...filters },
  });
  return response.data;
}
export async function getReceivablesReport(filters: ReportFilters) {
  const response = await apiClient.get<ReceivablesReport>("/reports/receivables", {
    params: { page: 1, page_size: 20, ...filters },
  });
  return response.data;
}
export async function getInventoryReport(filters: ReportFilters) {
  const response = await apiClient.get<InventoryReport>("/reports/inventory", {
    params: { page: 1, page_size: 20, ...filters },
  });
  return response.data;
}
export async function downloadReport(
  kind: ReportKind,
  filters: ReportFilters,
  format: "xlsx" | "csv" = "xlsx",
) {
  const response = await apiClient.get<Blob>(`/reports/${kind}`, {
    params: { ...filters, export: format },
    responseType: "blob",
    timeout: 60_000,
  });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `kabisa-${kind}-report.${format}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
