import { Blocks, CheckCircle2 } from "lucide-react";
import { useLocation } from "react-router-dom";

import { PageHeader } from "@/components/ui/page-header";
import { copy } from "@/lib/copy";

const moduleNames: Record<string, { title: string; area: string }> = {
  "/settings": { title: "Settings", area: "Configuration" },
};

export function PlaceholderPage() {
  const { pathname } = useLocation();
  const module = moduleNames[pathname] ?? { title: "Module", area: "Administration" };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={`${copy.placeholder.eyebrow} · ${module.area}`}
        title={`${module.title} ${copy.placeholder.titleSuffix}`}
        subtitle={copy.placeholder.subtitle}
      />
      <section className="surface-card overflow-hidden">
        <div className="grid min-h-[420px] lg:grid-cols-[.9fr_1.1fr]">
          <div className="flex flex-col justify-center border-b border-border bg-primary-50 p-8 lg:border-b-0 lg:border-r lg:p-12">
            <span className="flex size-12 items-center justify-center rounded-card bg-primary-100 text-primary-800">
              <Blocks aria-hidden="true" className="size-6" />
            </span>
            <h2 className="mt-6 max-w-md font-display text-2xl font-semibold tracking-tight">
              Production settings stay controlled and reviewable.
            </h2>
            <p className="mt-3 max-w-lg text-sm leading-6 text-secondary">
              Currency, inventory thresholds, company identity, and reporting defaults come
              from the settings table. Deployment secrets remain environment-only.
            </p>
          </div>
          <div className="flex flex-col justify-center p-8 lg:p-12">
            <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
              Managed configuration
            </p>
            <ul className="mt-5 space-y-4">
              {[
                "TZS currency and stock thresholds",
                "Company identity for report headers",
                "Environment-only authentication secrets",
                "Changes applied through reviewed operations",
              ].map((item) => (
                <li key={item} className="flex items-center gap-3 text-sm font-medium">
                  <CheckCircle2 aria-hidden="true" className="size-5 text-success" />
                  {item}
                </li>
              ))}
            </ul>
            <p className="mt-8 max-w-xl text-sm leading-6 text-secondary">
              See the operations runbook for safe configuration, migration, backup, and
              restore procedures.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
