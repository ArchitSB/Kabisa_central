import { ChevronDown, FlaskConical } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { useAuthStore } from "@/features/auth/auth-store";
import type { RoleListResponse } from "@/features/auth/types";
import { apiClient } from "@/lib/api-client";
import { formatRoleName } from "@/lib/utils";

const roleSwitcherEnabled = import.meta.env.VITE_ENABLE_ROLE_SWITCHER !== "false";

export function RoleSwitcher() {
  const user = useAuthStore((state) => state.user);
  const previewRole = useAuthStore((state) => state.previewRole);
  const setPreviewRole = useAuthStore((state) => state.setPreviewRole);
  const { data } = useQuery({
    queryKey: ["roles", "developer-preview"],
    queryFn: async () => {
      const response = await apiClient.get<RoleListResponse>("/roles", {
        params: { page: 1, page_size: 100, sort: "name" },
      });
      return response.data;
    },
    enabled: roleSwitcherEnabled && user?.role.name === "super_admin",
    staleTime: 5 * 60 * 1000,
  });

  if (!roleSwitcherEnabled || user?.role.name !== "super_admin") {
    return null;
  }

  const selectedRoleId = previewRole?.id ?? user.role.id;
  const roles = data?.items.filter((role) => role.is_system) ?? [];

  return (
    <div className="relative hidden items-center md:flex">
      <FlaskConical
        aria-hidden="true"
        className="pointer-events-none absolute left-3 size-3.5 text-primary-700"
      />
      <select
        aria-label="Dev viewing role"
        value={selectedRoleId}
        onChange={(event) => {
          const role = roles.find((item) => item.id === event.target.value);
          setPreviewRole(role?.id === user.role.id ? null : (role ?? null));
        }}
        className="h-10 appearance-none rounded-full border border-primary-200 bg-primary-50 pl-9 pr-9 text-xs font-semibold text-primary-900 transition-colors duration-standard hover:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-500/15"
      >
        {!roles.length ? (
          <option value={user.role.id}>
            Dev · Viewing as {formatRoleName(user.role.name)}
          </option>
        ) : null}
        {roles.map((role) => (
          <option key={role.id} value={role.id}>
            Dev · Viewing as {formatRoleName(role.name)}
          </option>
        ))}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute right-3 size-3.5 text-primary-700"
      />
    </div>
  );
}
