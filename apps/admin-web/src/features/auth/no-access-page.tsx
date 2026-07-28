import { ArrowLeft, ShieldX } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export function NoAccessPage() {
  return (
    <section
      className="surface-card mx-auto flex min-h-[420px] max-w-2xl flex-col items-center justify-center px-6 py-12 text-center"
      aria-labelledby="no-access-title"
    >
      <span className="flex size-14 items-center justify-center rounded-2xl bg-warning-surface text-warning">
        <ShieldX aria-hidden="true" className="size-7" />
      </span>
      <p className="mt-6 text-xs font-bold uppercase tracking-[0.14em] text-primary-700">
        Permission required
      </p>
      <h1
        id="no-access-title"
        className="mt-2 font-display text-3xl font-semibold tracking-tight text-foreground"
      >
        You don&apos;t have access to this area
      </h1>
      <p className="mt-3 max-w-lg text-sm leading-6 text-secondary">
        Your current role does not include the permission for this page. Ask a Kabisa
        administrator if you believe you need access.
      </p>
      <Button asChild className="mt-7">
        <Link to="/">
          <ArrowLeft aria-hidden="true" />
          Back to dashboard
        </Link>
      </Button>
    </section>
  );
}
