import type { ColumnDef } from "@tanstack/react-table";
import { format } from "date-fns";
import { Eye } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import type {
  OrderStatus,
  OrderSummary,
  PaymentStatus,
} from "@/features/orders/orders.data";
import { orderStatusLabels, paymentStatusLabels } from "@/features/orders/orders.data";
import { formatMoney } from "@/lib/utils";

export const orderTone: Record<
  OrderStatus,
  "success" | "warning" | "danger" | "neutral" | "info"
> = {
  PENDING: "warning",
  APPROVED: "info",
  PENDING_DELIVERY: "warning",
  DELIVERED: "success",
  FAILED: "danger",
  UNFOUND: "neutral",
  CANCELLED: "danger",
};
export const paymentTone: Record<PaymentStatus, "success" | "warning" | "danger"> = {
  UNPAID: "danger",
  PARTIAL: "warning",
  PAID: "success",
};

export function getOrderColumns(currency: string): ColumnDef<OrderSummary>[] {
  return [
    {
      accessorKey: "order_number",
      header: "Order #",
      cell: ({ row }) => (
        <Link
          to={`/orders/${row.original.id}`}
          className="rounded-md font-mono text-xs font-semibold text-primary-700 transition-colors duration-micro hover:text-primary-900 hover:underline"
        >
          {row.original.order_number}
        </Link>
      ),
    },
    {
      accessorKey: "customer_name",
      header: "Customer",
      cell: ({ row }) => (
        <span className="block max-w-[220px] truncate font-semibold">
          {row.original.customer_name}
        </span>
      ),
    },
    {
      accessorKey: "delivery_location",
      header: "Delivery location",
      cell: ({ row }) => (
        <span className="block max-w-[190px] truncate text-secondary">
          {row.original.delivery_location ?? "Not recorded"}
        </span>
      ),
    },
    {
      accessorKey: "payment_status",
      header: "Payment",
      cell: ({ row }) => (
        <StatusBadge
          label={paymentStatusLabels[row.original.payment_status]}
          tone={paymentTone[row.original.payment_status]}
        />
      ),
    },
    {
      accessorKey: "total_amount",
      header: "Total",
      meta: { align: "right" },
      cell: ({ row }) => (
        <span className="numeric font-semibold">
          {formatMoney(row.original.total_amount, currency)}
        </span>
      ),
    },
    {
      accessorKey: "item_count",
      header: "Items",
      meta: { align: "right" },
      cell: ({ row }) => <span className="numeric">{row.original.item_count}</span>,
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => (
        <span className="numeric text-xs text-secondary">
          {format(new Date(row.original.created_at), "dd MMM, HH:mm")}
        </span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <StatusBadge
          label={orderStatusLabels[row.original.status]}
          tone={orderTone[row.original.status]}
        />
      ),
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      meta: { align: "right" },
      cell: ({ row }) => (
        <Button asChild variant="outline" size="sm">
          <Link to={`/orders/${row.original.id}`}>
            <Eye aria-hidden="true" />
            View
          </Link>
        </Button>
      ),
    },
  ];
}
