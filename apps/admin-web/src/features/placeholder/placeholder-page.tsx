import { ArrowRight, Blocks, CheckCircle2 } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { copy } from "@/lib/copy";

const moduleNames: Record<string, { title: string; phase: string }> = {
  "/products": { title: "Products", phase: "Phase 2" },
  "/inventory": { title: "Inventory", phase: "Phase 2" },
  "/categories": { title: "Categories", phase: "Phase 2" },
  "/brands": { title: "Brands", phase: "Phase 2" },
  "/customers": { title: "Customers", phase: "Phase 3" },
  "/delivery-agents": { title: "Delivery agents", phase: "Phase 4" },
  "/coupons": { title: "Coupons", phase: "Phase 5" },
  "/reports": { title: "Reports", phase: "Phase 5" },
  "/roles": { title: "Roles & permissions", phase: "Phase 1" },
  "/settings": { title: "Settings", phase: "Phase 5" },
};

export function PlaceholderPage() {
  const { pathname } = useLocation();
  const module = moduleNames[pathname] ?? { title: "Module", phase: "Upcoming phase" };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={`${copy.placeholder.eyebrow} · ${module.phase}`}
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
              The shared foundation is already doing the repetitive work.
            </h2>
            <p className="mt-3 max-w-lg text-sm leading-6 text-secondary">
              This module inherits Kabisa tokens, the responsive shell, status language,
              forms, drawers, tables, focus handling, and reduced-motion behavior when its
              phase begins.
            </p>
          </div>
          <div className="flex flex-col justify-center p-8 lg:p-12">
            <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
              Foundation included
            </p>
            <ul className="mt-5 space-y-4">
              {[
                "Responsive navigation and page hierarchy",
                "Filter, bulk-action, data table, and pagination patterns",
                "Accessible drawer forms with validation",
                "Semantic status badges and restrained motion",
              ].map((item) => (
                <li key={item} className="flex items-center gap-3 text-sm font-medium">
                  <CheckCircle2 aria-hidden="true" className="size-5 text-success" />
                  {item}
                </li>
              ))}
            </ul>
            <Button asChild className="mt-8 w-fit">
              <Link to="/orders">
                Inspect the list pattern
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
