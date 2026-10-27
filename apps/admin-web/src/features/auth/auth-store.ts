import { create } from "zustand";
import { persist } from "zustand/middleware";
import axios from "axios";
import { queryClient } from "@/lib/query-client";

import { authClient } from "@/features/auth/auth-client";
import type {
  AccessTokenResponse,
  AuthUser,
  LoginResponse,
  RoleWithPermissions,
} from "@/features/auth/types";

type AuthStatus = "checking" | "authenticated" | "anonymous" | "unavailable";

function cachedUser(): AuthUser | null {
  try {
    return JSON.parse(
      sessionStorage.getItem("kabisa-admin-user") ?? "null",
    ) as AuthUser | null;
  } catch {
    return null;
  }
}

function rememberUser(user: AuthUser | null) {
  try {
    if (user) sessionStorage.setItem("kabisa-admin-user", JSON.stringify(user));
    else sessionStorage.removeItem("kabisa-admin-user");
  } catch {
    /* Storage can be disabled; session restore still works. */
  }
}

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  previewRole: RoleWithPermissions | null;
  status: AuthStatus;
  restoreError: unknown;
  sessionExpired: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  bootstrap: () => Promise<void>;
  setAccessToken: (accessToken: string) => void;
  setPreviewRole: (role: RoleWithPermissions | null) => void;
  clearSession: () => void;
  hasPermission: (code: string) => boolean;
};

let bootstrapPromise: Promise<void> | null = null;
let refreshPromise: Promise<string | null> | null = null;

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: cachedUser(),
      previewRole: null,
      status: "checking",
      restoreError: null,
      sessionExpired: false,

      login: async (email, password) => {
        const response = await authClient.post<LoginResponse>("/auth/login", {
          email,
          password,
        });
        set({
          accessToken: response.data.access_token,
          refreshToken: response.data.refresh_token,
          user: response.data.user,
          previewRole: null,
          status: "authenticated",
          sessionExpired: false,
        });
        rememberUser(response.data.user);
        return response.data.user;
      },

      logout: async () => {
        const accessToken = get().accessToken;
        try {
          if (accessToken) {
            await authClient.post("/auth/logout", undefined, {
              headers: {
                Authorization: `Bearer ${accessToken}`,
              },
            });
          }
        } finally {
          get().clearSession();
          set({ sessionExpired: false });
        }
      },

      bootstrap: async () => {
        if (get().status === "authenticated") return;
        if (bootstrapPromise) {
          return bootstrapPromise;
        }
        bootstrapPromise = (async () => {
          set({ status: "checking", restoreError: null });
          const { accessToken, refreshToken } = get();
          if (!accessToken && !refreshToken) {
            rememberUser(null);
            set({ status: "anonymous", user: null });
            return;
          }

          try {
            let currentAccessToken = accessToken;
            if (!currentAccessToken) {
              currentAccessToken = await refreshAccessToken();
            }
            if (!currentAccessToken) {
              get().clearSession();
              return;
            }

            try {
              const response = await authClient.get<AuthUser>("/auth/me", {
                headers: {
                  Authorization: `Bearer ${currentAccessToken}`,
                },
              });
              set({
                user: response.data,
                status: "authenticated",
              });
              rememberUser(response.data);
            } catch (error) {
              if (!axios.isAxiosError(error) || error.response?.status !== 401) throw error;
              const refreshedToken = await refreshAccessToken();
              if (!refreshedToken) {
                get().clearSession();
                return;
              }
              try {
                const response = await authClient.get<AuthUser>("/auth/me", {
                  headers: {
                    Authorization: `Bearer ${refreshedToken}`,
                  },
                });
                set({
                  user: response.data,
                  status: "authenticated",
                });
                rememberUser(response.data);
              } catch (error) {
                if (axios.isAxiosError(error) && error.response?.status === 401)
                  get().clearSession();
                else throw error;
              }
            }
          } catch (error) {
            set({ status: "unavailable", restoreError: error });
          }
        })().finally(() => {
          bootstrapPromise = null;
        });
        return bootstrapPromise;
      },

      setAccessToken: (accessToken) => set({ accessToken }),
      setPreviewRole: (previewRole) => set({ previewRole }),

      clearSession: () => {
        queryClient.clear();
        rememberUser(null);
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          previewRole: null,
          status: "anonymous",
          sessionExpired: true,
          restoreError: null,
        });
      },

      hasPermission: (code) => {
        const { previewRole, user } = get();
        const permissions = previewRole
          ? previewRole.permissions.map((permission) => permission.code)
          : user?.permissions;
        return Boolean(permissions?.includes(code));
      },
    }),
    {
      name: "kabisa-admin-auth",
      partialize: ({ accessToken, refreshToken }) => ({
        accessToken,
        refreshToken,
      }),
    },
  ),
);

export function useHasPermission(code: string): boolean {
  return useAuthStore((state) => {
    const permissions = state.previewRole
      ? state.previewRole.permissions.map((permission) => permission.code)
      : state.user?.permissions;
    return Boolean(permissions?.includes(code));
  });
}

export function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }
  refreshPromise = (async () => {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (!refreshToken) {
      return null;
    }
    try {
      const response = await authClient.post<AccessTokenResponse>("/auth/refresh", {
        refresh_token: refreshToken,
      });
      useAuthStore.getState().setAccessToken(response.data.access_token);
      return response.data.access_token;
    } catch (error) {
      if (axios.isAxiosError(error) && [401, 403].includes(error.response?.status ?? 0)) {
        useAuthStore.getState().clearSession();
        return null;
      }
      throw error;
    }
  })().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}
