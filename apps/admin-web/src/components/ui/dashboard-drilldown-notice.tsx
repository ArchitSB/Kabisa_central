import { X } from "lucide-react";

import { Button } from "@/components/ui/button";

type DashboardDrilldownNoticeProps = {
  title: string;
  description: string;
  onClear: () => void;
};

/** Makes dashboard-originated filters explicit and easy to leave. */
export function DashboardDrilldownNotice({
  title,
  description,
  onClear,
}: DashboardDrilldownNoticeProps) {
  return (
    <aside
      className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-primary-200 bg-primary-50 px-4 py-3"
      aria-label="Dashboard filter applied"
    >
      <div>
        <p className="text-xs font-semibold text-primary-900">{title}</p>
        <p className="mt-0.5 text-xs text-secondary">{description}</p>
      </div>
      <Button variant="ghost" size="sm" onClick={onClear}>
        <X aria-hidden="true" />
        Clear view
      </Button>
    </aside>
  );
}
