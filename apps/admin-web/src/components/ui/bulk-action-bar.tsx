import { ChevronDown } from "lucide-react";

import { Button } from "@/components/ui/button";

type BulkActionBarProps = {
  selectedCount: number;
  totalCount: number;
};

export function BulkActionBar({ selectedCount, totalCount }: BulkActionBarProps) {
  return (
    <div className="flex flex-col gap-3 rounded-control border border-border bg-surface px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <select
            aria-label="Bulk action"
            className="control-base h-9 min-w-[148px] appearance-none py-0 pr-9 text-xs font-semibold"
            disabled={selectedCount === 0}
            defaultValue=""
          >
            <option value="" disabled>
              Bulk action
            </option>
            <option value="approve">Approve orders</option>
            <option value="delivery">Send to delivery</option>
            <option value="cancel">Cancel orders</option>
          </select>
          <ChevronDown
            aria-hidden="true"
            className="pointer-events-none absolute right-3 top-1/2 size-3.5 -translate-y-1/2 text-muted"
          />
        </div>
        <Button variant="secondary" size="sm" disabled={selectedCount === 0}>
          Take action
        </Button>
        <span className="text-xs font-medium text-secondary">
          <strong className="numeric text-foreground">{selectedCount}</strong> selected
        </span>
      </div>
      <div className="flex items-center gap-3 text-xs text-secondary">
        <label className="flex items-center gap-2">
          <span>Sort</span>
          <select
            aria-label="Sort orders"
            className="h-8 rounded-full border border-border bg-surface px-3 pr-8 text-xs font-semibold text-foreground"
            defaultValue="newest"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="total">Highest total</option>
          </select>
        </label>
        <span className="whitespace-nowrap">
          <strong className="numeric text-foreground">{totalCount}</strong> records
        </span>
      </div>
    </div>
  );
}
