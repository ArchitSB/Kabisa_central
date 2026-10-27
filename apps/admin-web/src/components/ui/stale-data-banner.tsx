import { useSyncExternalStore } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { describeApiFailure } from "@/lib/api-errors";

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
  const failure = describeApiFailure(failed()[0]?.state.error);
  return (
    <div
      role="status"
      className="mb-4 flex flex-wrap items-center gap-3 rounded-control border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950"
    >
      <span>
        Couldn’t refresh some information. Showing the last loaded data. {failure.message}
        {failure.status ? ` HTTP ${failure.status}.` : ""}{" "}
        {failure.requestId ? `Request ${failure.requestId}` : ""}
      </span>
      <button
        type="button"
        className="font-semibold underline"
        onClick={() =>
          void client.refetchQueries({ predicate: (query) => failed().includes(query) })
        }
      >
        Try again
      </button>
    </div>
  );
}
