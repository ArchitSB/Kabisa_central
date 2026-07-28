import { create } from "zustand";
import { persist } from "zustand/middleware";

import { authClient } from "@/features/auth/auth-client";
import type { AccessTokenResponse, AuthUser, LoginResponse } from "@/features/auth/types";

type AuthStatus = "checking" | "authenticated" | "anonymous";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  bootstrap: () => Promise<void>;
  setAccessToken: (accessToken: string) => void;
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
      user: null,
      status: "checking",

      login: async (email, password) => {
        const response = await authClient.post<LoginResponse>("/auth/login", {
          email,
          password,
        });
        set({
          accessToken: response.data.access_token,
          refreshToken: response.data.refresh_token,
          user: response.data.user,
          status: "authenticated",
        });
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
        }
      },

      bootstrap: async () => {
        if (bootstrapPromise) {
          return bootstrapPromise;
        }
        bootstrapPromise = (async () => {
          const { accessToken, refreshToken } = get();
          if (!accessToken && !refreshToken) {
            set({ status: "anonymous", user: null });
            return;
          }

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
          } catch {
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
            } catch {
              get().clearSession();
            }
          }
        })().finally(() => {
          bootstrapPromise = null;
        });
        return bootstrapPromise;
      },

      setAccessToken: (accessToken) => set({ accessToken }),

      clearSession: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          status: "anonymous",
        }),

      hasPermission: (code) => Boolean(get().user?.permissions.includes(code)),
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
    } catch {
      useAuthStore.getState().clearSession();
      return null;
    }
  })().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}
