import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Pencil, Plus, Search, TicketPercent, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { useHasPermission } from "@/features/auth/auth-store";
import { getCatalogSettings } from "@/features/catalog/catalog-api";
import { CouponDrawer } from "@/features/coupons/coupon-drawer";
import { deleteCoupon, listCoupons, saveCoupon } from "@/features/coupons/coupons-api";
import type { Coupon } from "@/features/coupons/types";
import { getApiErrorDetail } from "@/lib/api-errors";
import { formatMoney } from "@/lib/utils";

const validityLabels = {
  VALID: "Valid",
  INACTIVE: "Inactive",
  UPCOMING: "Upcoming",
  EXPIRED: "Expired",
  EXHAUSTED: "Exhausted",
} as const;

export function CouponsPage() {
  const [search, setSearch] = useState("");
  const [active, setActive] = useState("");
  const [deleting, setDeleting] = useState<Coupon | null>(null);
  const deferredSearch = useDeferredValue(search.trim());
  const canCreate = useHasPermission("coupons.create");
  const canEdit = useHasPermission("coupons.edit");
  const canDelete = useHasPermission("coupons.delete");
  const queryClient = useQueryClient();
  const settings = useQuery({
    queryKey: ["catalog-settings"],
    queryFn: getCatalogSettings,
  });
  const currency = settings.data?.currency ?? "XXX";
  const query = useQuery({
    queryKey: ["coupons", deferredSearch, active],
    queryFn: () =>
      listCoupons({
        search: deferredSearch || undefined,
        is_active: active ? active === "active" : undefined,
      }),
  });
  const toggle = useMutation({
    mutationFn: (coupon: Coupon) =>
      saveCoupon({ ...coupon, is_active: !coupon.is_active }, coupon.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["coupons"] }),
    onError: (error) =>
      toast.error("Status could not be changed", { description: getApiErrorDetail(error) }),
  });
  const remove = useMutation({
    mutationFn: deleteCoupon,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["coupons"] });
      setDeleting(null);
      toast.success("Coupon removed");
    },
    onError: (error) =>
      toast.error("Coupon could not be removed", { description: getApiErrorDetail(error) }),
  });
  const columns = useMemo<ColumnDef<Coupon>[]>(
    () => [
      {
        accessorKey: "code",
        header: "Code",
        cell: ({ row }) => (
          <span className="font-mono text-xs font-bold text-primary-700">
            {row.original.code}
          </span>
        ),
      },
      {
        accessorKey: "name",
        header: "Name",
        cell: ({ row }) => <span className="font-semibold">{row.original.name}</span>,
      },
      {
        id: "discount",
        header: "Discount",
        cell: ({ row }) =>
          row.original.discount_type === "PERCENT"
            ? `${row.original.discount_value}%`
            : formatMoney(row.original.discount_value, currency),
      },
      {
        id: "validity",
        header: "Validity",
        cell: ({ row }) => (
          <div>
            <StatusBadge
              label={validityLabels[row.original.validity]}
              tone={
                row.original.validity === "VALID"
                  ? "success"
                  : row.original.validity === "EXPIRED"
                    ? "danger"
                    : "neutral"
              }
            />
            <p className="mt-1 text-[11px] text-secondary">
              {row.original.start_date} – {row.original.end_date}
            </p>
          </div>
        ),
      },
      {
        id: "usage",
        header: "Usage",
        cell: ({ row }) => (
          <span className="numeric">
            {row.original.used_count} / {row.original.usage_limit ?? "∞"}
          </span>
        ),
      },
      {
        accessorKey: "is_active",
        header: "Status",
        cell: ({ row }) =>
          canEdit ? (
            <button
              type="button"
              className="inline-flex min-h-10 cursor-pointer items-center rounded-full"
              aria-label={`${row.original.is_active ? "Deactivate" : "Activate"} ${row.original.code}`}
              onClick={() => toggle.mutate(row.original)}
            >
              <StatusBadge
                label={row.original.is_active ? "Active" : "Inactive"}
                tone={row.original.is_active ? "success" : "neutral"}
              />
            </button>
          ) : (
            <StatusBadge
              label={row.original.is_active ? "Active" : "Inactive"}
              tone={row.original.is_active ? "success" : "neutral"}
            />
          ),
      },
      ...(canEdit || canDelete
        ? [
            {
              id: "actions",
              header: "Actions",
              enableSorting: false,
              meta: { align: "right" as const },
              cell: ({ row }: { row: { original: Coupon } }) => (
                <div className="flex justify-end gap-1">
                  {canEdit ? (
                    <CouponDrawer
                      coupon={row.original}
                      trigger={
                        <Button variant="ghost" size="sm">
                          <Pencil aria-hidden="true" />
                          Edit
                        </Button>
                      }
                    />
                  ) : null}
                  {canDelete ? (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setDeleting(row.original)}
                    >
                      <Trash2 aria-hidden="true" />
                      Delete
                    </Button>
                  ) : null}
                </div>
              ),
            },
          ]
        : []),
    ],
    [canDelete, canEdit, currency, toggle],
  );
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Commercial controls"
        title="Coupons"
        subtitle="Manage bounded promotional discounts while tier pricing remains the primary B2B pricing mechanism."
        actions={
          canCreate ? (
            <CouponDrawer
              trigger={
                <Button>
                  <Plus aria-hidden="true" />
                  Create coupon
                </Button>
              }
            />
          ) : null
        }
      />
      <section className="surface-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
        <div className="relative w-full sm:max-w-md">
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
          />
          <Input
            type="search"
            className="pl-10"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search code or name"
            aria-label="Search coupons"
          />
        </div>
        <select
          className="control-base w-full sm:w-44"
          aria-label="Filter coupon status"
          value={active}
          onChange={(event) => setActive(event.target.value)}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <span className="sm:ml-auto text-sm text-secondary">
          <strong className="numeric text-foreground">{query.data?.total ?? 0}</strong>{" "}
          coupons
        </span>
      </section>
      {query.isPending ? (
        <LoadingState label="Loading coupons…" />
      ) : query.isError ? (
        <ErrorState title="Coupons could not be loaded" onRetry={() => query.refetch()} />
      ) : query.data.items.length === 0 && !search && !active ? (
        <EmptyState
          icon={TicketPercent}
          title="No coupons yet"
          description="Create the first bounded promotion when the commercial team needs one."
          action={
            canCreate ? (
              <CouponDrawer trigger={<Button>Create coupon</Button>} />
            ) : undefined
          }
        />
      ) : (
        <DataTable
          ariaLabel="Coupons"
          columns={columns}
          data={query.data.items}
          getRowId={(item) => item.id}
          selectable={false}
          pageSize={12}
        />
      )}
      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove coupon?"
        description={`This soft-deletes ${deleting?.code ?? "the coupon"}. Existing orders keep their coupon snapshot.`}
        confirmLabel="Remove coupon"
        destructive
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
      />
    </div>
  );
}
