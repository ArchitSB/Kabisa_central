import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  ArrowLeft,
  BadgeCheck,
  Building2,
  CalendarClock,
  Edit3,
  PackageCheck,
  ShieldCheck,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { useHasPermission } from "@/features/auth/auth-store";
import {
  getCatalogSettings,
  getProduct,
  listMovements,
  uploadUrl,
  verifyProduct,
} from "@/features/catalog/catalog-api";
import type { ProductDetail } from "@/features/catalog/types";
import { ProductDrawer } from "@/features/products/product-drawer";
import {
  PrescriptionBadge,
  ProductPlaceholder,
  ProductTypeBadge,
  StockBadge,
  VerificationBadge,
} from "@/features/products/product-ui";
import { getApiErrorDetail } from "@/lib/api-errors";
import { formatMoney } from "@/lib/utils";

const dateFormatter = new Intl.DateTimeFormat("en-TZ", { dateStyle: "medium" });
const dateTimeFormatter = new Intl.DateTimeFormat("en-TZ", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function ProductDetailPage() {
  const { productId = "" } = useParams();
  const canEdit = useHasPermission("products.edit");
  const canVerify = useHasPermission("products.verify");
  const queryClient = useQueryClient();
  const product = useQuery({
    queryKey: ["product", productId],
    queryFn: () => getProduct(productId),
    enabled: Boolean(productId),
  });
  const settings = useQuery({
    queryKey: ["catalog-settings"],
    queryFn: getCatalogSettings,
  });
  const movements = useQuery({
    queryKey: ["inventory", "movements", productId],
    queryFn: () => listMovements({ product_id: productId }),
    enabled: Boolean(productId),
  });
  const verification = useMutation({
    mutationFn: () => verifyProduct(productId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["product", productId] }),
        queryClient.invalidateQueries({ queryKey: ["products"] }),
      ]);
      toast.success("Product verified");
    },
    onError: (error) =>
      toast.error("Product could not be verified", {
        description: getApiErrorDetail(error),
      }),
  });
  const batchColumns = useMemo<ColumnDef<ProductDetail["batches"][number]>[]>(
    () => [
      { accessorKey: "warehouse_name", header: "Warehouse" },
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
    ],
    [],
  );
  if (product.isPending) return <LoadingState label="Loading product…" />;
  if (product.isError || !product.data)
    return (
      <ErrorState title="Product could not be loaded" onRetry={() => product.refetch()} />
    );
  const item = product.data;
  const currency = settings.data?.currency ?? "TZS";
  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/products">
          <ArrowLeft aria-hidden="true" />
          Back to products
        </Link>
      </Button>
      <PageHeader
        eyebrow={item.sku}
        title={item.name}
        subtitle={
          [item.generic_name, item.strength, item.pack_size].filter(Boolean).join(" · ") ||
          "Catalog product details"
        }
        actions={
          <>
            {canVerify && item.verification_status === "UNVERIFIED" ? (
              <Button
                variant="outline"
                disabled={verification.isPending}
                onClick={() => verification.mutate()}
              >
                <ShieldCheck aria-hidden="true" />
                {verification.isPending ? "Verifying…" : "Verify product"}
              </Button>
            ) : null}
            {canEdit ? (
              <ProductDrawer
                product={item}
                trigger={
                  <Button>
                    <Edit3 aria-hidden="true" />
                    Edit product
                  </Button>
                }
              />
            ) : null}
          </>
        }
      />
      <section className="surface-card grid gap-6 p-5 lg:grid-cols-[240px_1fr] lg:p-6">
        <div className="rounded-card border border-border bg-[#FBFCFB] p-4">
          {uploadUrl(item.primary_image) ? (
            <img
              src={uploadUrl(item.primary_image) ?? ""}
              alt={`${item.name} primary`}
              className="aspect-square w-full object-contain"
            />
          ) : (
            <div className="flex aspect-square items-center justify-center">
              <ProductPlaceholder />
            </div>
          )}
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <ProductTypeBadge type={item.product_type} />
            <VerificationBadge status={item.verification_status} />
            <StockBadge state={item.stock_status} onHand={item.on_hand} />
            {item.requires_prescription ? <PrescriptionBadge /> : null}
          </div>
          <p className="mt-5 max-w-3xl text-sm leading-6 text-secondary">
            {item.description || "No product description has been added."}
          </p>
          <dl className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Info label="Category" value={item.category.name} />
            <Info label="Brand" value={item.brand?.name ?? "Unbranded"} />
            <Info
              label="TMDA registration"
              value={item.registration_no ?? "Not recorded"}
            />
            <Info
              label="Unit / pack"
              value={`${item.unit}${item.pack_size ? ` · ${item.pack_size}` : ""}`}
            />
          </dl>
        </div>
      </section>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          icon={PackageCheck}
          label="Total on-hand"
          value={String(item.on_hand)}
          hint="Active, unexpired stock"
        />
        <Kpi
          icon={Building2}
          label="Warehouses"
          value={String(item.warehouse_stock.length)}
          hint="Locations currently holding stock"
        />
        <Kpi
          icon={BadgeCheck}
          label="Price tiers"
          value={String(item.prices.length)}
          hint="Complete active matrix"
        />
        <Kpi
          icon={CalendarClock}
          label="Batches"
          value={String(item.batches.length)}
          hint="Listed in FEFO order"
        />
      </section>
      <section className="grid gap-6 xl:grid-cols-2">
        <div className="surface-card p-5">
          <h2 className="font-display text-xl font-semibold">Stock by warehouse</h2>
          <div className="mt-4 divide-y divide-border">
            {item.warehouse_stock.length ? (
              item.warehouse_stock.map((stock) => (
                <div
                  key={stock.warehouse_id}
                  className="flex items-center justify-between py-3"
                >
                  <span>
                    <span className="block font-semibold">{stock.warehouse_name}</span>
                    <span className="font-mono text-xs text-secondary">
                      {stock.warehouse_code}
                    </span>
                  </span>
                  <strong className="numeric text-lg">{stock.on_hand}</strong>
                </div>
              ))
            ) : (
              <p className="py-8 text-center text-sm text-secondary">No available stock.</p>
            )}
          </div>
        </div>
        <div className="surface-card p-5">
          <h2 className="font-display text-xl font-semibold">Price matrix</h2>
          <div className="mt-4 divide-y divide-border">
            {item.prices.length ? (
              item.prices.map((price) => (
                <div key={price.id} className="flex items-center justify-between py-3">
                  <span>
                    <span className="block font-semibold">{price.price_tier.name}</span>
                    <span className="font-mono text-xs text-secondary">
                      {price.price_tier.code}
                    </span>
                  </span>
                  <strong className="numeric text-lg">
                    {formatMoney(Number(price.price), currency)}
                  </strong>
                </div>
              ))
            ) : (
              <p className="py-8 text-center text-sm text-secondary">
                No tier prices entered.
              </p>
            )}
          </div>
        </div>
      </section>
      <section>
        <div className="mb-3">
          <h2 className="font-display text-xl font-semibold">Batches</h2>
          <p className="mt-1 text-sm text-secondary">
            FEFO order; expired batches are excluded from on-hand totals.
          </p>
        </div>
        <DataTable
          ariaLabel={`${item.name} batches`}
          columns={batchColumns}
          data={item.batches}
          getRowId={(batch) => batch.id}
          selectable={false}
          pageSize={10}
        />
      </section>
      <section className="surface-card p-5">
        <h2 className="font-display text-xl font-semibold">Movement history</h2>
        <div className="mt-5 space-y-0">
          {movements.data?.items.length ? (
            movements.data.items.map((movement, index) => (
              <div key={movement.id} className="relative flex gap-4 pb-5 last:pb-0">
                <div className="relative z-10 mt-1 size-3 shrink-0 rounded-full border-[3px] border-primary-100 bg-primary-700" />
                {index < movements.data.items.length - 1 ? (
                  <div
                    aria-hidden="true"
                    className="absolute left-[5px] top-4 h-full w-px bg-border"
                  />
                ) : null}
                <div className="flex min-w-0 flex-1 flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="font-semibold">
                      {movement.movement_type}{" "}
                      <span
                        className={movement.quantity > 0 ? "text-success" : "text-danger"}
                      >
                        {movement.quantity > 0 ? "+" : ""}
                        {movement.quantity}
                      </span>
                    </p>
                    <p className="text-sm text-secondary">
                      {movement.warehouse_name}
                      {movement.batch_number ? ` · Batch ${movement.batch_number}` : ""}
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
            <p className="py-8 text-center text-sm text-secondary">No movement history.</p>
          )}
        </div>
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-[0.06em] text-secondary">
        {label}
      </dt>
      <dd className="mt-1 font-medium">{value}</dd>
    </div>
  );
}
function Kpi({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: typeof PackageCheck;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <article className="surface-card p-5">
      <span className="flex size-9 items-center justify-center rounded-control bg-primary-50 text-primary-700">
        <Icon aria-hidden="true" className="size-[18px]" />
      </span>
      <p className="mt-4 text-xs font-semibold uppercase tracking-[0.06em] text-secondary">
        {label}
      </p>
      <p className="numeric mt-1 font-display text-3xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-secondary">{hint}</p>
    </article>
  );
}
