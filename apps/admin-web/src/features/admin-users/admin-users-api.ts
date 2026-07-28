import type { RoleSummary } from "@/features/auth/types";
import { apiClient } from "@/lib/api-client";

export type AdminUser = {
  id: string;
  name: string;
  email: string;
  role: RoleSummary;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminUserListResponse = {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
};

export type AdminUserPayload = {
  name: string;
  email: string;
  role_id: string;
  is_active: boolean;
  password?: string;
};

export async function listAdminUsers(search: string): Promise<AdminUserListResponse> {
  const response = await apiClient.get<AdminUserListResponse>("/admin-users", {
    params: {
      page: 1,
      page_size: 100,
      sort: "name",
      search: search || undefined,
    },
  });
  return response.data;
}

export async function createAdminUser(payload: AdminUserPayload): Promise<AdminUser> {
  const response = await apiClient.post<AdminUser>("/admin-users", payload);
  return response.data;
}

export async function updateAdminUser(
  userId: string,
  payload: AdminUserPayload,
): Promise<AdminUser> {
  const response = await apiClient.patch<AdminUser>(`/admin-users/${userId}`, payload);
  return response.data;
}
