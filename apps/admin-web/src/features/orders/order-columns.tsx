import type { ColumnDef } from "@tanstack/react-table";
import { format } from "date-fns";
import { Eye, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  type OrderStatus,
  type PaymentStatus,
  type PreviewOrder,
  orderStatusLabels,
  paymentStatusLabels,
} from "@/features/orders/orders.data";
import { formatMoney } from "@/lib/utils";

const orderTone: Record<
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

const paymentTone: Record<PaymentStatus, "success" | "warning" | "danger"> = {
  UNPAID: "danger",
  PARTIAL: "warning",
  PAID: "success",
};

export function getOrderColumns(currency: string): ColumnDef<PreviewOrder>[] {
  return [
    {
      accessorKey: "orderNumber",
      header: "Order #",
      cell: ({ row }) => (
        <button
          type="button"
          className="rounded-md font-mono text-xs font-semibold text-primary-700 transition-colors duration-micro hover:text-primary-900 hover:underline"
          onClick={() =>
            toast.info(row.original.orderNumber, {
              description: "Live order detail arrives in Phase 4.",
            })
          }
        >
          {row.original.orderNumber}
        </button>
      ),
    },
    {
      accessorKey: "customer",
      header: "Customer",
      cell: ({ row }) => (
        <div className="max-w-[210px] truncate font-semibold" title={row.original.customer}>
          {row.original.customer}
        </div>
      ),
    },
    {
      accessorKey: "location",
      header: "Delivery location",
      cell: ({ row }) => (
        <span
          className="block max-w-[190px] truncate text-secondary"
          title={row.original.location}
        >
          {row.original.location}
        </span>
      ),
    },
    {
      accessorKey: "paymentStatus",
      header: "Payment",
      cell: ({ row }) => (
        <StatusBadge
          label={paymentStatusLabels[row.original.paymentStatus]}
          tone={paymentTone[row.original.paymentStatus]}
        />
      ),
    },
    {
      accessorKey: "total",
      header: "Total",
      meta: { align: "right" },
      cell: ({ row }) => (
        <span className="numeric font-semibold">
          {formatMoney(row.original.total, currency)}
        </span>
      ),
    },
    {
      accessorKey: "items",
      header: "Items",
      meta: { align: "right" },
      cell: ({ row }) => (
        <span className="numeric text-secondary">{row.original.items}</span>
      ),
    },
    {
      accessorKey: "createdAt",
      header: "Created",
      cell: ({ row }) => (
        <span className="numeric text-xs text-secondary">
          {format(new Date(row.original.createdAt), "dd MMM, HH:mm")}
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
        <div className="flex justify-end gap-1.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => toast.info(`Viewing ${row.original.orderNumber}`)}
          >
            <Eye aria-hidden="true" />
            View
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => toast.info(`Editing ${row.original.orderNumber}`)}
          >
            <Pencil aria-hidden="true" />
            Edit
          </Button>
          <Button
            aria-label={`Delete ${row.original.orderNumber}`}
            title="Soft delete begins with the live order module"
            variant="destructive"
            size="icon"
            className="size-8 min-h-8 rounded-full"
            disabled
          >
            <Trash2 aria-hidden="true" />
          </Button>
        </div>
      ),
    },
  ];
}
