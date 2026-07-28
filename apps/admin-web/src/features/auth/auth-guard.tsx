import { useEffect } from "react";
import { LoaderCircle } from "lucide-react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuthStore } from "@/features/auth/auth-store";

export function AuthGuard() {
  const location = useLocation();
  const status = useAuthStore((state) => state.status);
  const bootstrap = useAuthStore((state) => state.bootstrap);

  useEffect(() => {
    if (status === "checking") {
      void bootstrap();
    }
  }, [bootstrap, status]);

  if (status === "checking") {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-background px-6"
        role="status"
        aria-live="polite"
      >
        <div className="text-center">
          <LoaderCircle
            aria-hidden="true"
            className="mx-auto size-6 animate-spin text-primary-700"
          />
          <p className="mt-3 text-sm font-medium text-secondary">
            Restoring your secure workspace…
          </p>
        </div>
      </div>
    );
  }

  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
