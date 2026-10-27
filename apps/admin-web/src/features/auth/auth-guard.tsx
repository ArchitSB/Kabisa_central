import { useEffect } from "react";
import { LoaderCircle } from "lucide-react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuthStore } from "@/features/auth/auth-store";
import { AppLayout } from "@/app/app-layout";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";

export function AuthGuard() {
  const location = useLocation();
  const status = useAuthStore((state) => state.status);
  const bootstrap = useAuthStore((state) => state.bootstrap);
  const user = useAuthStore((state) => state.user);
  const restoreError = useAuthStore((state) => state.restoreError);

  useEffect(() => {
    if (status === "checking") {
      void bootstrap();
    }
  }, [bootstrap, status]);

  if (status === "unavailable") {
    return (
      <ErrorState
        title="Your workspace could not be restored"
        error={restoreError}
        onRetry={() => void bootstrap()}
      />
    );
  }

  if (status === "checking" && user) {
    // Cached identity is only used for the shell; protected pages wait for /auth/me.
    return (
      <AppLayout>
        <LoadingState label="Restoring your secure workspace…" />
      </AppLayout>
    );
  }
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
