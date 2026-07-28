export type RoleSummary = {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
};

export type Permission = {
  id: string;
  code: string;
  description: string;
  group: string;
};

export type RoleWithPermissions = RoleSummary & {
  permissions: Permission[];
  created_at: string;
  updated_at: string;
};

export type RoleListResponse = {
  items: RoleWithPermissions[];
  total: number;
  page: number;
  page_size: number;
};

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
  last_login_at: string | null;
  role: RoleSummary;
  permissions: string[];
};

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type AccessTokenResponse = {
  access_token: string;
  token_type: "bearer";
};

export type ApiErrorResponse = {
  detail: string;
  code: string;
};
