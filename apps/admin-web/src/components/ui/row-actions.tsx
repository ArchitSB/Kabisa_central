import type { ReactNode } from "react";
import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function RowActions({ children }: { children: ReactNode }) {
  return <div className="flex justify-end gap-1">{children}</div>;
}

export function DeleteRowAction({
  label,
  onClick,
  disabled = false,
  className,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      disabled={disabled}
      aria-label={label}
      className={cn(
        "border-danger/30 text-danger hover:border-danger/50 hover:bg-danger-surface hover:text-danger",
        className,
      )}
      onClick={onClick}
    >
      <Trash2 aria-hidden="true" />
      Delete
    </Button>
  );
}
