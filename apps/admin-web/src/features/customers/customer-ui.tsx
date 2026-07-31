import { StatusBadge } from "@/components/ui/status-badge";
import type {
  BusinessType,
  CustomerStatus,
  DocumentStatus,
} from "@/features/customers/types";
import { businessTypeLabels } from "@/features/customers/customer-options";

export function CustomerStatusBadge({ status }: { status: CustomerStatus }) {
  const config = {
    PENDING: ["Pending", "neutral"],
    UNDER_REVIEW: ["Under review", "warning"],
    VERIFIED: ["Verified", "success"],
    REJECTED: ["Rejected", "danger"],
    SUSPENDED: ["Suspended", "danger"],
  }[status] as [string, "neutral" | "warning" | "success" | "danger"];
  return <StatusBadge label={config[0]} tone={config[1]} />;
}

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  const tone =
    status === "APPROVED" ? "success" : status === "REJECTED" ? "danger" : "warning";
  return (
    <StatusBadge
      label={
        status === "APPROVED" ? "Approved" : status === "REJECTED" ? "Rejected" : "Pending"
      }
      tone={tone}
    />
  );
}

export function BusinessTypeBadge({ type }: { type: BusinessType }) {
  return <StatusBadge label={businessTypeLabels[type]} tone="info" />;
}
