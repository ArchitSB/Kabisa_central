import { Pill, ShieldAlert } from "lucide-react";

import { StatusBadge } from "@/components/ui/status-badge";
import type { ProductType, StockState, VerificationStatus } from "@/features/catalog/types";
import { productTypeLabels } from "@/features/products/product-options";

export function ProductTypeBadge({ type }: { type: ProductType }) {
  const tone =
    type === "PRESCRIPTION" || type === "SPECIALTY"
      ? "warning"
      : type === "MEDICAL_DEVICE"
        ? "info"
        : "neutral";
  return <StatusBadge label={productTypeLabels[type]} tone={tone} />;
}

export function StockBadge({ state, onHand }: { state: StockState; onHand: number }) {
  return (
    <StatusBadge
      label={`${onHand} ${state === "out" ? "out" : state === "low" ? "low" : "on hand"}`}
      tone={state === "out" ? "danger" : state === "low" ? "warning" : "success"}
    />
  );
}

export function VerificationBadge({ status }: { status: VerificationStatus }) {
  return (
    <StatusBadge
      label={status === "VERIFIED" ? "Verified" : "Unverified"}
      tone={status === "VERIFIED" ? "success" : "warning"}
    />
  );
}

export function PrescriptionBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-danger-surface px-2.5 py-1 text-xs font-semibold text-danger">
      <ShieldAlert aria-hidden="true" className="size-3.5" />
      Prescription (POM)
    </span>
  );
}

export function ProductPlaceholder() {
  return (
    <span className="flex size-11 items-center justify-center rounded-control border border-border bg-primary-50 text-primary-700">
      <Pill aria-hidden="true" className="size-5" />
    </span>
  );
}
