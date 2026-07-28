import type {
  Permission,
  RoleListResponse,
  RoleWithPermissions,
} from "@/features/auth/types";
import { apiClient } from "@/lib/api-client";

export type PermissionListResponse = {
  items: Permission[];
  total: number;
  page: number;
  page_size: number;
};

export type RolePayload = {
  name: string;
  description: string;
  permission_codes: string[];
};

export async function listRoles(): Promise<RoleListResponse> {
  const response = await apiClient.get<RoleListResponse>("/roles", {
    params: { page: 1, page_size: 100, sort: "name" },
  });
  return response.data;
}

export async function listPermissions(): Promise<PermissionListResponse> {
  const response = await apiClient.get<PermissionListResponse>("/roles/permissions", {
    params: { page: 1, page_size: 100 },
  });
  return response.data;
}

export async function createRole(payload: RolePayload): Promise<RoleWithPermissions> {
  const response = await apiClient.post<RoleWithPermissions>("/roles", payload);
  return response.data;
}

export async function updateRole(
  roleId: string,
  payload: RolePayload,
): Promise<RoleWithPermissions> {
  const response = await apiClient.patch<RoleWithPermissions>(`/roles/${roleId}`, payload);
  return response.data;
}
