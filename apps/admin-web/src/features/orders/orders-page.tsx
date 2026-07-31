import { useCallback, useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RotateCcw, Search } from "lucide-react";
import { toast } from "sonner";

import { BulkActionBar } from "@/components/ui/bulk-action-bar";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { FilterBar, FilterField } from "@/components/ui/filter-bar";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { getCatalogSettings, listWarehouses } from "@/features/catalog/catalog-api";
import { useHasPermission } from "@/features/auth/auth-store";
import { CreateOrderDrawer } from "@/features/orders/create-order-drawer";
import { getOrderColumns } from "@/features/orders/order-columns";
import {
  bulkOrderStatus,
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
  const deferredSearch = useDeferredValue(search.trim());
  const canCreate = useHasPermission("orders.create");
  const canApprove = useHasPermission("orders.approve");
  const canCancel = useHasPermission("orders.cancel");
  const canStatus = useHasPermission("orders.status");
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
  });
  const settings = useQuery({
    queryKey: ["catalog-settings"],
    queryFn: getCatalogSettings,
  });
  const warehouses = useQuery({
    queryKey: ["warehouses", "order-filter"],
    queryFn: () => listWarehouses(),
  });
  const bulk = useMutation({
    mutationFn: ({ ids, target }: { ids: string[]; target: OrderStatus }) =>
      bulkOrderStatus(ids, target),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["orders"] });
      setSelected([]);
      if (Object.keys(result.failed).length) {
        toast.warning(`${result.updated.length} orders updated`, {
          description: `${Object.keys(result.failed).length} could not be changed.`,
        });
      } else toast.success(`${result.updated.length} orders updated`);
    },
    onError: (error) =>
      toast.error("Bulk action failed", { description: getApiErrorDetail(error) }),
  });
  const columns = useMemo(
    () => getOrderColumns(settings.data?.currency ?? "XXX"),
    [settings.data?.currency],
  );
  const handleSelection = useCallback((rows: OrderSummary[]) => setSelected(rows), []);
  const actions = [
    ...(canApprove ? [{ value: "APPROVED", label: "Approve" }] : []),
    ...(canCancel ? [{ value: "CANCELLED", label: "Cancel" }] : []),
    ...(canStatus
      ? [
          { value: "FAILED", label: "Mark failed" },
          { value: "UNFOUND", label: "Mark unfound" },
        ]
      : []),
  ];

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
          canCreate ? (
            <CreateOrderDrawer
              trigger={
                <Button>
                  <Plus aria-hidden="true" />
                  Create order
                </Button>
              }
            />
          ) : null
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
          <div className="relative">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
            />
            <Input
              id="order-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Order number or customer"
              className="pl-10"
            />
          </div>
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

      <BulkActionBar
        selectedCount={selected.length}
        totalCount={orders.data.total}
        noun="orders"
        pending={bulk.isPending}
        showSort={false}
        actions={actions}
        onAction={(target) =>
          bulk.mutate({
            ids: selected.map((item) => item.id),
            target: target as OrderStatus,
          })
        }
      />
      <DataTable
        ariaLabel="Kabisa orders"
        columns={columns}
        data={orders.data.items}
        getRowId={(order) => order.id}
        pageSize={10}
        selectable={actions.length > 0}
        onSelectionChange={handleSelection}
      />
    </div>
  );
}
