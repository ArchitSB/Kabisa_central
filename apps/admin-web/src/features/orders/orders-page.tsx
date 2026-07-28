import { useCallback, useMemo, useState } from "react";
import { Plus, RotateCcw, Search } from "lucide-react";

import { BulkActionBar } from "@/components/ui/bulk-action-bar";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { EntityDrawer } from "@/components/ui/entity-drawer";
import { FilterBar, FilterField } from "@/components/ui/filter-bar";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { useHasPermission } from "@/features/auth/auth-store";
import { getOrderColumns } from "@/features/orders/order-columns";
import {
  type OrderStatus,
  type PaymentStatus,
  type PreviewOrder,
  orderStatusLabels,
  previewOrders,
} from "@/features/orders/orders.data";
import { copy } from "@/lib/copy";
import { cn } from "@/lib/utils";

type StatusFilter = "ALL" | OrderStatus;
type PaymentFilter = "ALL" | PaymentStatus;

const orderStatusOptions: OrderStatus[] = [
  "PENDING",
  "APPROVED",
  "PENDING_DELIVERY",
  "DELIVERED",
  "FAILED",
  "UNFOUND",
  "CANCELLED",
];
const statusTabs: StatusFilter[] = ["ALL", ...orderStatusOptions];

export function OrdersPage() {
  const currency = "TZS";
  const canCreateOrders = useHasPermission("orders.create");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<StatusFilter>("ALL");
  const [payment, setPayment] = useState<PaymentFilter>("ALL");
  const [fromDate, setFromDate] = useState("");
  const [selectedCount, setSelectedCount] = useState(0);

  const columns = useMemo(() => getOrderColumns(currency), [currency]);

  const filteredOrders = useMemo(() => {
    const query = search.trim().toLowerCase();
    return previewOrders.filter((order) => {
      const matchesQuery =
        !query ||
        order.orderNumber.toLowerCase().includes(query) ||
        order.customer.toLowerCase().includes(query);
      const matchesStatus = status === "ALL" || order.status === status;
      const matchesPayment = payment === "ALL" || order.paymentStatus === payment;
      const matchesDate = !fromDate || order.createdAt.slice(0, 10) >= fromDate;
      return matchesQuery && matchesStatus && matchesPayment && matchesDate;
    });
  }, [fromDate, payment, search, status]);

  const handleSelectionChange = useCallback((rows: PreviewOrder[]) => {
    setSelectedCount(rows.length);
  }, []);

  function resetFilters() {
    setSearch("");
    setStatus("ALL");
    setPayment("ALL");
    setFromDate("");
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={copy.orders.eyebrow}
        title={copy.orders.title}
        subtitle={copy.orders.subtitle}
        actions={
          canCreateOrders ? (
            <EntityDrawer
              trigger={
                <Button>
                  <Plus aria-hidden="true" />
                  {copy.orders.create}
                </Button>
              }
            />
          ) : null
        }
      />

      <div className="scrollbar-subtle -mx-1 overflow-x-auto px-1">
        <div className="flex min-w-max items-center gap-1 rounded-control border border-border bg-surface p-1.5">
          {statusTabs.map((tab) => {
            const label = tab === "ALL" ? "All orders" : orderStatusLabels[tab];
            const count =
              tab === "ALL"
                ? previewOrders.length
                : previewOrders.filter((order) => order.status === tab).length;
            return (
              <button
                key={tab}
                type="button"
                aria-pressed={status === tab}
                onClick={() => setStatus(tab)}
                className={cn(
                  "flex h-8 items-center gap-2 rounded-lg px-3 text-xs font-semibold text-secondary transition-colors duration-standard hover:bg-primary-50 hover:text-primary-800",
                  status === tab &&
                    "bg-primary-700 text-white shadow-sm hover:bg-primary-700 hover:text-white",
                )}
              >
                {label}
                <span
                  className={cn(
                    "numeric rounded-full bg-neutral-surface px-1.5 py-0.5 text-[10px] text-neutral",
                    status === tab && "bg-white/15 text-white",
                  )}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <FilterBar>
        <FilterField label={copy.orders.searchLabel} htmlFor="order-search">
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
              placeholder={copy.orders.searchPlaceholder}
              className="pl-10"
            />
          </div>
        </FilterField>
        <FilterField label={copy.orders.statusLabel} htmlFor="order-status">
          <select
            id="order-status"
            value={status}
            onChange={(event) => setStatus(event.target.value as StatusFilter)}
            className="control-base w-full"
          >
            <option value="ALL">All statuses</option>
            {orderStatusOptions.map((value) => (
              <option key={value} value={value}>
                {orderStatusLabels[value]}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label={copy.orders.paymentLabel} htmlFor="payment-status">
          <select
            id="payment-status"
            value={payment}
            onChange={(event) => setPayment(event.target.value as PaymentFilter)}
            className="control-base w-full"
          >
            <option value="ALL">All payments</option>
            <option value="UNPAID">Unpaid</option>
            <option value="PARTIAL">Partial</option>
            <option value="PAID">Paid</option>
          </select>
        </FilterField>
        <FilterField label={copy.orders.fromLabel} htmlFor="from-date">
          <Input
            id="from-date"
            type="date"
            value={fromDate}
            onChange={(event) => setFromDate(event.target.value)}
          />
        </FilterField>
        <Button variant="ghost" className="w-full xl:w-auto" onClick={resetFilters}>
          <RotateCcw aria-hidden="true" />
          {copy.orders.reset}
        </Button>
      </FilterBar>

      <BulkActionBar selectedCount={selectedCount} totalCount={filteredOrders.length} />
      <DataTable
        ariaLabel="Orders"
        columns={columns}
        data={filteredOrders}
        getRowId={(order) => order.id}
        onSelectionChange={handleSelectionChange}
      />
    </div>
  );
}
