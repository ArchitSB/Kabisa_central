export type RoleSummary = {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
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
