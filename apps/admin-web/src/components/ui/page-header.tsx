import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  subtitle: string;
  actions?: ReactNode;
  className?: string;
};

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between",
        className,
      )}
    >
      <div className="max-w-3xl">
        {eyebrow ? (
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="font-display text-[30px] font-semibold leading-[1.14] tracking-[-0.025em] text-foreground sm:text-[34px]">
          {title}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-secondary">{subtitle}</p>
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </header>
  );
}
