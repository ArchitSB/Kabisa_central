import { apiClient } from "@/lib/api-client";

import type { AuditFilters, AuditLogList, AuditOptions } from "./types";

export async function listAuditLogs(filters: AuditFilters): Promise<AuditLogList> {
  const response = await apiClient.get<AuditLogList>("/audit", { params: filters });
  return response.data;
}

export async function getAuditOptions(): Promise<AuditOptions> {
  const response = await apiClient.get<AuditOptions>("/audit/options");
  return response.data;
}
