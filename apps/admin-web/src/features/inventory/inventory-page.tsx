import { useDeferredValue, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  Boxes,
  CalendarClock,
  CircleDollarSign,
  History,
  PackagePlus,
  Search,
  SlidersHorizontal,
  TriangleAlert,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { FilterBar, FilterField } from "@/components/ui/filter-bar";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { useHasPermission } from "@/features/auth/auth-store";
import {
  getInventorySummary,
  listBatches,
  listInventory,
  listMovements,
  listWarehouses,
} from "@/features/catalog/catalog-api";
import type { InventoryProduct, ProductBatch } from "@/features/catalog/types";
import { AdjustBatchDrawer, InboundBatchDrawer } from "@/features/inventory/batch-drawers";
import { StockBadge } from "@/features/products/product-ui";
import { formatMoney } from "@/lib/utils";

const dateFormatter = new Intl.DateTimeFormat("en-TZ", { dateStyle: "medium" });
const dateTimeFormatter = new Intl.DateTimeFormat("en-TZ", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function InventoryPage() {
  const [warehouseId, setWarehouseId] = useState("");
  const [search, setSearch] = useState("");
  const [stock, setStock] = useState("");
  const [batchStatus, setBatchStatus] = useState("");
  const deferredSearch = useDeferredValue(search.trim());
  const canAdd = useHasPermission("batches.create");
  const canAdjust = useHasPermission("inventory.adjust");
  const warehouses = useQuery({
    queryKey: ["warehouses", "inventory"],
    queryFn: () => listWarehouses(),
  });
  const summary = useQuery({
    queryKey: ["inventory", "summary", warehouseId],
    queryFn: () => getInventorySummary(warehouseId || undefined),
  });
  const inventory = useQuery({
    queryKey: ["inventory", "products", warehouseId, deferredSearch, stock],
    queryFn: () =>
      listInventory({
        search: deferredSearch || undefined,
        warehouse_id: warehouseId || undefined,
        stock: stock || undefined,
      }),
  });
  const batches = useQuery({
    queryKey: ["batches", warehouseId, batchStatus],
    queryFn: () =>
      listBatches({
        warehouse_id: warehouseId || undefined,
        batch_status: batchStatus || undefined,
      }),
  });
  const movements = useQuery({
    queryKey: ["inventory", "movements", warehouseId],
    queryFn: () => listMovements({ warehouse_id: warehouseId || undefined }),
  });
  const productColumns = useMemo<ColumnDef<InventoryProduct>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Product",
        cell: ({ row }) => (
          <div>
            <Link
              to={`/products/${row.original.product_id}`}
              className="font-semibold hover:text-primary-800 hover:underline"
            >
              {row.original.name}
            </Link>
            <span className="block font-mono text-xs text-secondary">
              {row.original.sku}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "on_hand",
        header: "On-hand",
        cell: ({ row }) => (
          <StockBadge state={row.original.stock_status} onHand={row.original.on_hand} />
        ),
      },
      {
        accessorKey: "low_stock_threshold",
        header: "Reorder point",
        meta: { align: "right" },
        cell: ({ row }) => (
          <span className="numeric">{row.original.low_stock_threshold}</span>
        ),
      },
      {
        accessorKey: "warehouse_stock",
        header: "Warehouse breakdown",
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-1.5">
            {row.original.warehouse_stock.length ? (
              row.original.warehouse_stock.map((item) => (
                <span
                  key={item.warehouse_id}
                  className="rounded-full bg-neutral-surface px-2.5 py-1 text-xs font-semibold text-neutral"
                >
                  {item.warehouse_code}: {item.on_hand}
                </span>
              ))
            ) : (
              <span className="text-secondary">No stock</span>
            )}
          </div>
        ),
      },
    ],
    [],
  );
  const batchColumns = useMemo<ColumnDef<ProductBatch>[]>(
    () => [
      {
        accessorKey: "product_name",
        header: "Product",
        cell: ({ row }) => (
          <div>
            <Link
              to={`/products/${row.original.product_id}`}
              className="font-semibold hover:text-primary-800 hover:underline"
            >
              {row.original.product_name}
            </Link>
            <span className="block font-mono text-xs text-secondary">
              {row.original.product_sku}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "warehouse_name",
        header: "Warehouse",
        cell: ({ row }) => (
          <div>
            <span className="block font-medium">{row.original.warehouse_name}</span>
            <span className="font-mono text-xs text-secondary">
              {row.original.warehouse_code}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "batch_number",
        header: "Batch #",
        cell: ({ row }) => (
          <span className="font-mono text-xs">{row.original.batch_number}</span>
        ),
      },
      {
        accessorKey: "expiry_date",
        header: "Expiry (FEFO)",
        cell: ({ row }) => (
          <span
            className={
              row.original.is_expired
                ? "font-semibold text-danger"
                : row.original.is_expiring_soon
                  ? "font-semibold text-warning"
                  : "text-secondary"
            }
          >
            {dateFormatter.format(new Date(`${row.original.expiry_date}T00:00:00`))}
            {row.original.is_expiring_soon ? " · Soon" : ""}
          </span>
        ),
      },
      {
        accessorKey: "quantity_available",
        header: "Available",
        meta: { align: "right" },
        cell: ({ row }) => (
          <span className="numeric">{row.original.quantity_available}</span>
        ),
      },
      {
        accessorKey: "quantity_reserved",
        header: "Reserved",
        meta: { align: "right" },
        cell: ({ row }) => (
          <span className="numeric text-secondary">{row.original.quantity_reserved}</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <StatusBadge
            label={row.original.status}
            tone={
              row.original.is_expired
                ? "danger"
                : row.original.is_expiring_soon
                  ? "warning"
                  : row.original.status === "ACTIVE"
                    ? "success"
                    : "neutral"
            }
          />
        ),
      },
      ...(canAdjust
        ? [
            {
              id: "actions",
              header: "Actions",
              enableSorting: false,
              meta: { align: "right" as const },
              cell: ({ row }: { row: { original: ProductBatch } }) => (
                <AdjustBatchDrawer
                  batch={row.original}
                  trigger={
                    <Button variant="ghost" size="sm">
                      <SlidersHorizontal aria-hidden="true" />
                      Adjust
                    </Button>
                  }
                />
              ),
            },
          ]
        : []),
    ],
    [canAdjust],
  );
  if (summary.isPending || inventory.isPending || batches.isPending)
    return <LoadingState label="Loading inventory…" />;
  if (
    summary.isError ||
    inventory.isError ||
    batches.isError ||
    !summary.data ||
    !inventory.data ||
    !batches.data
  )
    return (
      <ErrorState
        title="Inventory could not be loaded"
        onRetry={() => {
          summary.refetch();
          inventory.refetch();
          batches.refetch();
        }}
      />
    );
  const kpis = [
    {
      label: "Total items",
      value: String(summary.data.total_items),
      hint: "Active catalog products",
      icon: Boxes,
    },
    {
      label: "Stock value",
      value: formatMoney(Number(summary.data.stock_value), summary.data.currency),
      hint: summary.data.cost_missing_batches
        ? `${summary.data.cost_missing_batches} batches missing cost`
        : "Cost-based valuation",
      icon: CircleDollarSign,
    },
    {
      label: "Low stock",
      value: String(summary.data.low_stock_count),
      hint: `${summary.data.out_of_stock_count} out of stock`,
      icon: TriangleAlert,
    },
    {
      label: "Expiring soon",
      value: String(summary.data.expiring_soon_count),
      hint: "Active stock within 90 days",
      icon: CalendarClock,
    },
  ];
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Inventory control"
        title="Inventory"
        subtitle="Monitor warehouse stock, expiry exposure, cost valuation, and every quantity movement."
        actions={
          canAdd ? (
            <InboundBatchDrawer
              trigger={
                <Button>
                  <PackagePlus aria-hidden="true" />
                  Add inbound batch
                </Button>
              }
            />
          ) : null
        }
      />
      <FilterBar title="Inventory filters">
        <FilterField label="Search products" htmlFor="inventory-search">
          <div className="relative">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
            />
            <Input
              id="inventory-search"
              type="search"
              className="pl-10"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Name or SKU"
            />
          </div>
        </FilterField>
        <FilterField label="Warehouse" htmlFor="inventory-warehouse">
          <select
            id="inventory-warehouse"
            className="control-base w-full"
            value={warehouseId}
            onChange={(event) => setWarehouseId(event.target.value)}
          >
            <option value="">All warehouses</option>
            {warehouses.data?.items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Stock" htmlFor="inventory-stock">
          <select
            id="inventory-stock"
            className="control-base w-full"
            value={stock}
            onChange={(event) => setStock(event.target.value)}
          >
            <option value="">All stock levels</option>
            <option value="in">In stock</option>
            <option value="low">Low stock</option>
            <option value="out">Out of stock</option>
          </select>
        </FilterField>
        <FilterField label="Batch status" htmlFor="batch-status">
          <select
            id="batch-status"
            className="control-base w-full"
            value={batchStatus}
            onChange={(event) => setBatchStatus(event.target.value)}
          >
            <option value="">All batch statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="DEPLETED">Depleted</option>
            <option value="EXPIRED">Expired</option>
            <option value="QUARANTINED">Quarantined</option>
          </select>
        </FilterField>
      </FilterBar>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map(({ label, value, hint, icon: Icon }) => (
          <article key={label} className="surface-card p-5">
            <span className="flex size-9 items-center justify-center rounded-control bg-primary-50 text-primary-700">
              <Icon aria-hidden="true" className="size-[18px]" />
            </span>
            <p className="mt-4 text-xs font-semibold uppercase tracking-[0.06em] text-secondary">
              {label}
            </p>
            <p className="numeric mt-1 font-display text-3xl font-semibold">{value}</p>
            <p className="mt-1 text-xs text-secondary">{hint}</p>
          </article>
        ))}
      </section>
      <section>
        <div className="mb-3">
          <h2 className="font-display text-xl font-semibold">Stock by product</h2>
          <p className="mt-1 text-sm text-secondary">
            On-hand excludes expired, quarantined, deleted, and reserved quantities.
          </p>
        </div>
        <DataTable
          ariaLabel="Inventory product rollup"
          columns={productColumns}
          data={inventory.data.items}
          getRowId={(item) => item.product_id}
          selectable={false}
          pageSize={10}
        />
      </section>
      <section>
        <div className="mb-3">
          <h2 className="font-display text-xl font-semibold">Batches</h2>
          <p className="mt-1 text-sm text-secondary">
            Warehouse-scoped batches listed earliest-expiry-first.
          </p>
        </div>
        <DataTable
          ariaLabel="Inventory batches"
          columns={batchColumns}
          data={batches.data.items}
          getRowId={(item) => item.id}
          selectable={false}
          pageSize={10}
        />
      </section>
      <section className="surface-card p-5">
        <div className="flex items-center gap-2">
          <History aria-hidden="true" className="size-5 text-primary-700" />
          <h2 className="font-display text-xl font-semibold">Movement timeline</h2>
        </div>
        <div className="mt-5">
          {movements.data?.items.length ? (
            movements.data.items.map((movement, index) => (
              <div key={movement.id} className="relative flex gap-4 pb-5 last:pb-0">
                <span className="relative z-10 mt-1 size-3 shrink-0 rounded-full border-[3px] border-primary-100 bg-primary-700" />
                {index < movements.data.items.length - 1 ? (
                  <span
                    aria-hidden="true"
                    className="absolute left-[5px] top-4 h-full w-px bg-border"
                  />
                ) : null}
                <div className="flex min-w-0 flex-1 flex-col gap-1 sm:flex-row sm:justify-between">
                  <div>
                    <p className="font-semibold">
                      {movement.product_name}{" "}
                      <span
                        className={movement.quantity > 0 ? "text-success" : "text-danger"}
                      >
                        {movement.quantity > 0 ? "+" : ""}
                        {movement.quantity}
                      </span>
                    </p>
                    <p className="text-sm text-secondary">
                      {movement.movement_type} · {movement.warehouse_name}
                      {movement.batch_number ? ` · ${movement.batch_number}` : ""}
                      {movement.note ? ` · ${movement.note}` : ""}
                    </p>
                  </div>
                  <time className="whitespace-nowrap text-xs text-secondary">
                    {dateTimeFormatter.format(new Date(movement.created_at))}
                  </time>
                </div>
              </div>
            ))
          ) : (
            <p className="py-8 text-center text-sm text-secondary">
              No movements match this warehouse.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
