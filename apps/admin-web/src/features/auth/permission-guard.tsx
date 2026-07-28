import { Outlet } from "react-router-dom";

import { NoAccessPage } from "@/features/auth/no-access-page";
import { useAuthStore } from "@/features/auth/auth-store";

type PermissionGuardProps = {
  permission: string;
};

export function PermissionGuard({ permission }: PermissionGuardProps) {
  const allowed = useAuthStore((state) => state.hasPermission(permission));
  return allowed ? <Outlet /> : <NoAccessPage />;
}
