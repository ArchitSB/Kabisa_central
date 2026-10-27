import { AlertCircle, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { describeApiFailure } from "@/lib/api-errors";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="surface-card flex min-h-64 items-center justify-center" role="status">
      <LoaderCircle aria-hidden="true" className="size-6 animate-spin text-primary-700" />
      <span className="ml-3 text-sm font-medium text-secondary">{label}</span>
    </div>
  );
}

export function ErrorState({
  title = "This content could not be loaded",
  onRetry,
  error,
}: {
  title?: string;
  onRetry: () => void;
  error?: unknown;
}) {
  const failure = describeApiFailure(error);
  return (
    <div className="surface-card flex min-h-64 flex-col items-center justify-center px-6 text-center">
      <AlertCircle aria-hidden="true" className="size-7 text-danger" />
      <p className="mt-3 font-semibold">{title}</p>
      <p className="mt-1 text-sm text-secondary" role="alert">
        {failure.message}
      </p>
      {(failure.status || failure.requestId) && (
        <p className="mt-2 break-all text-xs text-secondary">
          {[
            failure.status && `HTTP ${failure.status}`,
            failure.requestId && `Request ${failure.requestId}`,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}
      <Button type="button" variant="secondary" className="mt-5" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}
