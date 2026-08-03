import { type ReactElement, type ReactNode } from "react";
import { ResponsiveContainer, Tooltip, type TooltipProps } from "recharts";

import { cn } from "@/lib/utils";

export function ChartContainer({
  children,
  className,
}: {
  children: ReactElement;
  className?: string;
}) {
  return (
    <div className={cn("h-[240px] min-w-0", className)}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

export function ChartTooltip({ content }: { content: ReactElement }) {
  return (
    <Tooltip cursor={{ stroke: "#C4E2EA", strokeDasharray: "4 4" }} content={content} />
  );
}

export function ChartTooltipContent({
  active,
  label,
  payload,
  formatter,
}: TooltipProps<number, string> & {
  formatter: (value: number) => ReactNode;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-control border border-border bg-surface px-3 py-2 shadow-card">
      <p className="text-[11px] font-semibold text-secondary">{label}</p>
      <p className="numeric mt-1 text-sm font-bold text-foreground">
        {formatter(Number(payload[0]?.value ?? 0))}
      </p>
    </div>
  );
}
