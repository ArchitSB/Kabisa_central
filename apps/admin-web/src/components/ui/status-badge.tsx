import { AlertCircle, CheckCircle2, Circle, Clock3, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type StatusTone = "success" | "warning" | "danger" | "neutral" | "info";

const toneStyles: Record<StatusTone, string> = {
  success: "bg-success-surface text-success",
  warning: "bg-warning-surface text-warning",
  danger: "bg-danger-surface text-danger",
  neutral: "bg-neutral-surface text-neutral",
  info: "bg-primary-100 text-primary-800",
};

const toneIcons: Record<StatusTone, LucideIcon> = {
  success: CheckCircle2,
  warning: Clock3,
  danger: AlertCircle,
  neutral: Circle,
  info: Circle,
};

type StatusBadgeProps = {
  label: string;
  tone?: StatusTone;
  className?: string;
};

export function StatusBadge({ label, tone = "neutral", className }: StatusBadgeProps) {
  const Icon = toneIcons[tone];
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold",
        toneStyles[tone],
        className,
      )}
    >
      <Icon aria-hidden="true" className="size-3" strokeWidth={2.5} />
      {label}
    </span>
  );
}
