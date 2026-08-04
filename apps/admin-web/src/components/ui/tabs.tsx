import { useId, useState } from "react";

import { cn } from "@/lib/utils";

export type TabItem = {
  value: string;
  label: string;
  count?: number;
  content: React.ReactNode;
};

export function Tabs({
  items,
  defaultValue,
  ariaLabel,
}: {
  items: TabItem[];
  defaultValue?: string;
  ariaLabel: string;
}) {
  const instanceId = useId();
  const [active, setActive] = useState(defaultValue ?? items[0]?.value);
  const current = items.find((item) => item.value === active) ?? items[0];

  return (
    <div>
      <div
        role="tablist"
        aria-label={ariaLabel}
        className="scrollbar-subtle flex gap-1 overflow-x-auto border-b border-border"
      >
        {items.map((item) => {
          const selected = item.value === current?.value;
          return (
            <button
              key={item.value}
              id={`${instanceId}-${item.value}-tab`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`${instanceId}-${item.value}-panel`}
              tabIndex={selected ? 0 : -1}
              className={cn(
                "relative min-h-12 whitespace-nowrap px-4 text-sm font-semibold text-secondary transition-colors duration-standard hover:text-primary-800",
                selected &&
                  "text-primary-800 after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:bg-primary-700",
              )}
              onClick={() => setActive(item.value)}
              onKeyDown={(event) => {
                if (
                  event.key !== "ArrowLeft" &&
                  event.key !== "ArrowRight" &&
                  event.key !== "Home" &&
                  event.key !== "End"
                )
                  return;
                event.preventDefault();
                const index = items.findIndex(
                  (candidate) => candidate.value === item.value,
                );
                const direction = event.key === "ArrowRight" ? 1 : -1;
                const next =
                  event.key === "Home"
                    ? items[0]
                    : event.key === "End"
                      ? items.at(-1)
                      : items[(index + direction + items.length) % items.length];
                if (!next) return;
                setActive(next.value);
                document.getElementById(`${instanceId}-${next.value}-tab`)?.focus();
              }}
            >
              {item.label}
              {item.count !== undefined ? (
                <span className="numeric ml-2 rounded-full bg-neutral-surface px-2 py-0.5 text-[11px] text-neutral">
                  {item.count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      {current ? (
        <div
          id={`${instanceId}-${current.value}-panel`}
          role="tabpanel"
          aria-labelledby={`${instanceId}-${current.value}-tab`}
          className="pt-5"
        >
          {current.content}
        </div>
      ) : null}
    </div>
  );
}
