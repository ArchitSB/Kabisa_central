import type { ReactNode } from "react";
import { Search, SlidersHorizontal } from "lucide-react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type FilterBarProps = {
  children: ReactNode;
  title?: string;
  className?: string;
};

export function FilterBar({ children, title = "Filters", className }: FilterBarProps) {
  return (
    <section className={cn("surface-card p-4 sm:p-5", className)} aria-label={title}>
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
        <span className="flex size-8 items-center justify-center rounded-lg bg-primary-50 text-primary-700">
          <SlidersHorizontal aria-hidden="true" className="size-4" />
        </span>
        {title}
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(220px,1.6fr)_repeat(3,minmax(140px,1fr))_auto] xl:items-end">
        {children}
      </div>
    </section>
  );
}

type FieldProps = {
  label: string;
  htmlFor: string;
  children: ReactNode;
  className?: string;
};

export function FilterField({ label, htmlFor, children, className }: FieldProps) {
  return (
    <div className={cn("min-w-0", className)}>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 block text-xs font-semibold text-secondary"
      >
        {label}
      </label>
      {children}
    </div>
  );
}

type SearchInputProps = {
  id?: string;
  value: string;
  onValueChange: (value: string) => void;
  placeholder: string;
  ariaLabel?: string;
};

export function SearchInput({
  id,
  value,
  onValueChange,
  placeholder,
  ariaLabel,
}: SearchInputProps) {
  return (
    <div className="relative">
      <Search
        aria-hidden="true"
        className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
      />
      <Input
        id={id}
        type="search"
        className="pl-10"
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
      />
    </div>
  );
}
