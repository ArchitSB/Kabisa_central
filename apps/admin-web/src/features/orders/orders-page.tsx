import { useCallback, useMemo, useState } from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { Download, Plus, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import { BulkActionBar } from "@/components/ui/bulk-action-bar";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { FilterBar, FilterField, SearchInput } from "@/components/ui/filter-bar";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { getCatalogSettings, listWarehouses } from "@/features/catalog/catalog-api";
import { useHasPermission } from "@/features/auth/auth-store";
import { CreateOrderDrawer } from "@/features/orders/create-order-drawer";
import { getOrderColumns } from "@/features/orders/order-columns";
import {
  deleteOrder,
  listDeliveryAgents,
  listOrders,
  type OrderFilters,
} from "@/features/orders/orders-api";
import type {
  OrderStatus,
  OrderSummary,
  PaymentStatus,
} from "@/features/orders/orders.data";
import { orderStatusLabels } from "@/features/orders/orders.data";
import { getApiErrorDetail } from "@/lib/api-errors";
import { bulkResultMessage, downloadSection, runBulkAction } from "@/lib/data-controls";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { cn } from "@/lib/utils";

type StatusFilter = "ALL" | OrderStatus;
const statusTabs: StatusFilter[] = [
  "ALL",
  "PENDING",
  "APPROVED",
  "PENDING_DELIVERY",
  "DELIVERED",
  "FAILED",
  "UNFOUND",
  "CANCELLED",
];

export function OrdersPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<StatusFilter>("ALL");
  const [payment, setPayment] = useState<"" | PaymentStatus>("");
  const [warehouse, setWarehouse] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [selected, setSelected] = useState<OrderSummary[]>([]);
  const [deleting, setDeleting] = useState<OrderSummary | null>(null);
  const deferredSearch = useDebouncedValue(search.trim());
  const canCreate = useHasPermission("orders.create");
  const canApprove = useHasPermission("orders.approve");
  const canCancel = useHasPermission("orders.cancel");
  const canStatus = useHasPermission("orders.status");
  const canAssign = useHasPermission("deliveries.assign");
  const canDelete = useHasPermission("orders.cancel");
  const canExport = useHasPermission("reports.export");
  const queryClient = useQueryClient();
  const filters: OrderFilters = {
    search: deferredSearch || undefined,
    order_status: status === "ALL" ? undefined : status,
    payment_status: payment || undefined,
    warehouse_id: warehouse || undefined,
    date_from: fromDate || undefined,
    date_to: toDate || undefined,
  };
  const orders = useQuery({
    queryKey: ["orders", filters],
    queryFn: () => listOrders(filters),
    placeholderData: keepPreviousData,
  });
  const settings = useQuery({
    queryKey: ["catalog-settings"],
    queryFn: getCatalogSettings,
  });
  const warehouses = useQuery({
    queryKey: ["warehouses", "order-filter"],
    queryFn: () => listWarehouses(),
  });
  const agents = useQuery({
    queryKey: ["delivery-agents", "bulk-options"],
    queryFn: () => listDeliveryAgents({ is_active: true }),
    enabled: canAssign,
  });
  const bulk = useMutation({
    mutationFn: ({ action, value }: { action: string; value?: string }) =>
      runBulkAction("/orders/bulk", {
        ids: selected.map((item) => item.id),
        action,
        value,
      }),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["orders"] });
      setSelected([]);
      const message = bulkResultMessage(result);
      if (result.skipped || result.failed)
        toast.warning(message.title, { description: message.description });
      else toast.success(message.title);
    },
    onError: (error) =>
      toast.error("Bulk action failed", { description: getApiErrorDetail(error) }),
  });
  const remove = useMutation({
    mutationFn: deleteOrder,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["orders"] });
      setDeleting(null);
      toast.success("Order removed");
    },
    onError: (error) =>
      toast.error("Order could not be removed", {
        description: getApiErrorDetail(error),
      }),
  });
  const columns = useMemo(
    () =>
      getOrderColumns(settings.data?.currency ?? "XXX", {
        canDelete,
        onDelete: setDeleting,
      }),
    [canDelete, settings.data?.currency],
  );
  const handleSelection = useCallback((rows: OrderSummary[]) => setSelected(rows), []);
  const actions = [
    ...(canApprove ? [{ value: "approve", label: "Approve" }] : []),
    ...(canCancel ? [{ value: "cancel", label: "Cancel" }] : []),
    ...(canStatus
      ? [
          { value: "fail", label: "Mark failed" },
          { value: "unfound", label: "Mark unfound" },
        ]
      : []),
    ...(canAssign
      ? [
          {
            value: "assign_delivery",
            label: "Assign delivery agent",
            options:
              agents.data?.items.map((agent) => ({
                value: agent.id,
                label: agent.name,
              })) ?? [],
          },
        ]
      : []),
    ...(canExport ? [{ value: "export", label: "Export selected" }] : []),
  ];

  async function downloadOrders(ids?: string[]) {
    try {
      await downloadSection(
        "/orders/export",
        { ...filters, ids },
        ids ? "kabisa-selected-orders.xlsx" : "kabisa-orders.xlsx",
      );
      toast.success("Orders downloaded");
    } catch (error) {
      toast.error("Orders could not be downloaded", {
        description: getApiErrorDetail(error),
      });
    }
  }

  if (orders.isPending) return <LoadingState label="Loading orders…" />;
  if (orders.isError || !orders.data) {
    return (
      <ErrorState title="Orders could not be loaded" onRetry={() => orders.refetch()} />
    );
  }
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Orders, payments & delivery"
        title="Orders"
        subtitle="Create verified-customer orders, reserve warehouse stock, reconcile payments, and complete delivery."
        actions={
          <>
            {canExport ? (
              <Button variant="secondary" onClick={() => downloadOrders()}>
                <Download aria-hidden="true" />
                Download
              </Button>
            ) : null}
            {canCreate ? (
              <CreateOrderDrawer
                trigger={
                  <Button>
                    <Plus aria-hidden="true" />
                    Create order
                  </Button>
                }
              />
            ) : null}
          </>
        }
      />

      <div className="scrollbar-subtle -mx-1 overflow-x-auto px-1">
        <div className="flex min-w-max items-center gap-1 rounded-control border border-border bg-surface p-1.5">
          {statusTabs.map((tab) => (
            <button
              key={tab}
              type="button"
              aria-pressed={status === tab}
              onClick={() => setStatus(tab)}
              className={cn(
                "flex h-8 cursor-pointer items-center gap-2 rounded-lg px-3 text-xs font-semibold text-secondary transition-colors duration-standard hover:bg-primary-50 hover:text-primary-800",
                status === tab &&
                  "bg-primary-700 text-white shadow-sm hover:bg-primary-700 hover:text-white",
              )}
            >
              {tab === "ALL" ? "All orders" : orderStatusLabels[tab]}
              <span
                className={cn(
                  "numeric rounded-full bg-neutral-surface px-1.5 py-0.5 text-[10px] text-neutral",
                  status === tab && "bg-white/15 text-white",
                )}
              >
                {orders.data.status_counts[tab] ?? 0}
              </span>
            </button>
          ))}
        </div>
      </div>

      <FilterBar className="[&>div:last-child]:xl:grid-cols-4">
        <FilterField label="Search" htmlFor="order-search">
          <SearchInput
            id="order-search"
            value={search}
            onValueChange={setSearch}
            placeholder="Order number or customer"
          />
        </FilterField>
        <FilterField label="Payment" htmlFor="payment-status">
          <select
            id="payment-status"
            value={payment}
            onChange={(event) => setPayment(event.target.value as "" | PaymentStatus)}
            className="control-base w-full"
          >
            <option value="">All payments</option>
            <option value="UNPAID">Unpaid</option>
            <option value="PARTIAL">Partial</option>
            <option value="PAID">Paid</option>
          </select>
        </FilterField>
        <FilterField label="Warehouse" htmlFor="order-warehouse-filter">
          <select
            id="order-warehouse-filter"
            value={warehouse}
            onChange={(event) => setWarehouse(event.target.value)}
            className="control-base w-full"
          >
            <option value="">All warehouses</option>
            {warehouses.data?.items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="From" htmlFor="order-from">
          <Input
            id="order-from"
            type="date"
            value={fromDate}
            onChange={(event) => setFromDate(event.target.value)}
          />
        </FilterField>
        <FilterField label="To" htmlFor="order-to">
          <Input
            id="order-to"
            type="date"
            value={toDate}
            onChange={(event) => setToDate(event.target.value)}
          />
        </FilterField>
        <div className="flex items-end">
          <Button
            variant="secondary"
            className="w-full"
            onClick={() => {
              setSearch("");
              setStatus("ALL");
              setPayment("");
              setWarehouse("");
              setFromDate("");
              setToDate("");
            }}
          >
            <RotateCcw aria-hidden="true" />
            Reset
          </Button>
        </div>
      </FilterBar>

      {actions.length ? (
        <BulkActionBar
          selectedCount={selected.length}
          totalCount={orders.data.total}
          noun="orders"
          pending={bulk.isPending}
          showSort={false}
          actions={actions}
          onAction={(action, value) => {
            if (action === "export") {
              void downloadOrders(selected.map((item) => item.id));
            } else bulk.mutate({ action, value });
          }}
        />
      ) : null}
      <DataTable
        ariaLabel="Kabisa orders"
        columns={columns}
        data={orders.data.items}
        getRowId={(order) => order.id}
        pageSize={10}
        selectable={actions.length > 0}
        onSelectionChange={handleSelection}
      />
      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove order?"
        description="Only pending or cancelled orders without recorded payments can be soft-deleted. Committed orders must remain auditable."
        confirmLabel="Remove order"
        destructive
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
      />
    </div>
  );
}
