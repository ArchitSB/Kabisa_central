import { useSyncExternalStore } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@kabisa/api-client";

export function StaleDataBanner() {
  const client = useQueryClient();
  const cache = client.getQueryCache();
  const failed = () =>
    cache
      .getAll()
      .filter(
        (query) =>
          query.isActive() &&
          query.state.data !== undefined &&
          query.state.status === "error",
      );
  const signature = useSyncExternalStore(
    (notify) => cache.subscribe(notify),
    () =>
      failed()
        .map((query) => `${query.queryHash}:${query.state.errorUpdatedAt}`)
        .join("|"),
  );
  if (!signature) return null;
  const error = failed()[0]?.state.error;
  const failure =
    error instanceof ApiError
      ? error
      : {
          message: "Check your connection.",
          status: undefined,
          requestId: undefined,
        };
  return (
    <div role="status" className="container notice">
      <span>
        Couldn’t refresh some information. Showing the last loaded data.{" "}
        {failure.message}
        {failure.status ? ` HTTP ${failure.status}.` : ""}{" "}
        {failure.requestId ? `Request ${failure.requestId}` : ""}
      </span>
      <button
        type="button"
        className="font-semibold underline"
        onClick={() =>
          void client.refetchQueries({
            predicate: (query) => failed().includes(query),
          })
        }
      >
        Try again
      </button>
    </div>
  );
}
