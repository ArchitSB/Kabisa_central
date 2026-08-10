import { useEffect, useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";

import { Button } from "@/components/ui/button";

type BulkActionBarProps = {
  selectedCount: number;
  totalCount: number;
  actions?: Array<{
    value: string;
    label: string;
    options?: Array<{ value: string; label: string }>;
  }>;
  onAction?: (action: string, value?: string) => void;
  pending?: boolean;
  noun?: string;
  showSort?: boolean;
};

const defaultActions = [
  { value: "approve", label: "Approve orders" },
  { value: "delivery", label: "Send to delivery" },
  { value: "cancel", label: "Cancel orders" },
];

export function BulkActionBar({
  selectedCount,
  totalCount,
  actions = defaultActions,
  onAction,
  pending = false,
  noun = "records",
  showSort = true,
}: BulkActionBarProps) {
  const [action, setAction] = useState("");
  const [value, setValue] = useState("");
  const selectedAction = useMemo(
    () => actions.find((item) => item.value === action),
    [action, actions],
  );

  useEffect(() => {
    if (selectedCount === 0) {
      setAction("");
      setValue("");
    }
  }, [selectedCount]);
  return (
    <div className="flex flex-col gap-3 rounded-control border border-border bg-surface px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <select
            aria-label="Bulk action"
            className="control-base h-9 min-w-[148px] appearance-none py-0 pr-9 text-xs font-semibold"
            disabled={selectedCount === 0}
            value={action}
            onChange={(event) => {
              setAction(event.target.value);
              setValue("");
            }}
          >
            <option value="" disabled>
              Bulk action
            </option>
            {actions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <ChevronDown
            aria-hidden="true"
            className="pointer-events-none absolute right-3 top-1/2 size-3.5 -translate-y-1/2 text-muted"
          />
        </div>
        {selectedAction?.options ? (
          <div className="relative">
            <select
              aria-label={`${selectedAction.label} option`}
              className="control-base h-9 min-w-[168px] appearance-none py-0 pr-9 text-xs font-semibold"
              value={value}
              onChange={(event) => setValue(event.target.value)}
            >
              <option value="" disabled>
                Select option
              </option>
              {selectedAction.options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <ChevronDown
              aria-hidden="true"
              className="pointer-events-none absolute right-3 top-1/2 size-3.5 -translate-y-1/2 text-muted"
            />
          </div>
        ) : null}
        <Button
          variant="secondary"
          size="sm"
          disabled={
            selectedCount === 0 ||
            !action ||
            pending ||
            Boolean(selectedAction?.options && !value)
          }
          onClick={() => {
            onAction?.(action, value || undefined);
            setAction("");
            setValue("");
          }}
        >
          {pending ? "Working…" : "Take action"}
        </Button>
        <span className="text-xs font-medium text-secondary">
          <strong className="numeric text-foreground">{selectedCount}</strong> selected
        </span>
      </div>
      <div className="flex items-center gap-3 text-xs text-secondary">
        {showSort ? (
          <label className="flex items-center gap-2">
            <span>Sort</span>
            <select
              aria-label="Sort records"
              className="h-8 rounded-full border border-border bg-surface px-3 pr-8 text-xs font-semibold text-foreground"
              defaultValue="newest"
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </label>
        ) : null}
        <span className="whitespace-nowrap">
          <strong className="numeric text-foreground">{totalCount}</strong> {noun}
        </span>
      </div>
    </div>
  );
}
