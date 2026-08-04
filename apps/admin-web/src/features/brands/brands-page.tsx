import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { BadgeCheck, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { useHasPermission } from "@/features/auth/auth-store";
import { BrandDrawer } from "@/features/brands/brand-drawer";
import {
  deleteBrand,
  listBrands,
  saveBrand,
  uploadUrl,
} from "@/features/catalog/catalog-api";
import type { Brand } from "@/features/catalog/types";
import { getApiErrorDetail } from "@/lib/api-errors";
import { getInitials } from "@/lib/utils";

export function BrandsPage() {
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState<Brand | null>(null);
  const deferredSearch = useDeferredValue(search.trim());
  const canCreate = useHasPermission("brands.create");
  const canEdit = useHasPermission("brands.edit");
  const canDelete = useHasPermission("brands.delete");
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["brands", deferredSearch],
    queryFn: () => listBrands(deferredSearch),
  });
  const remove = useMutation({
    mutationFn: deleteBrand,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["brands"] });
      setDeleting(null);
      toast.success("Brand removed");
    },
    onError: (error) =>
      toast.error("Brand could not be removed", { description: getApiErrorDetail(error) }),
  });
  const toggle = useMutation({
    mutationFn: (brand: Brand) =>
      saveBrand(
        { name: brand.name, logo_path: brand.logo_path, is_active: !brand.is_active },
        brand.id,
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["brands"] }),
    onError: (error) =>
      toast.error("Status could not be changed", { description: getApiErrorDetail(error) }),
  });
  const columns = useMemo<ColumnDef<Brand>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Brand",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            {uploadUrl(row.original.logo_path) ? (
              <img
                src={uploadUrl(row.original.logo_path) ?? ""}
                alt=""
                className="size-10 rounded-control border border-border object-contain p-1"
              />
            ) : (
              <span className="flex size-10 items-center justify-center rounded-control bg-primary-50 text-xs font-bold text-primary-800">
                {getInitials(row.original.name)}
              </span>
            )}
            <span>
              <span className="block font-semibold">{row.original.name}</span>
              <span className="block font-mono text-xs text-secondary">
                /{row.original.slug}
              </span>
            </span>
          </div>
        ),
      },
      {
        accessorKey: "is_active",
        header: "Status",
        cell: ({ row }) =>
          canEdit ? (
            <button
              type="button"
              className="inline-flex min-h-10 items-center rounded-full"
              aria-label={`Set ${row.original.name} ${row.original.is_active ? "inactive" : "active"}`}
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
              cell: ({ row }: { row: { original: Brand } }) => (
                <div className="flex justify-end gap-1">
                  {canEdit ? (
                    <BrandDrawer
                      brand={row.original}
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
    [canDelete, canEdit, toggle],
  );
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Catalog partners"
        title="Brands"
        subtitle="Maintain supplier brands and Kabisa-owned product lines."
        actions={
          canCreate ? (
            <BrandDrawer
              trigger={
                <Button>
                  <Plus aria-hidden="true" />
                  Add brand
                </Button>
              }
            />
          ) : null
        }
      />
      <section className="surface-card flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
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
            placeholder="Search brands"
            aria-label="Search brands"
          />
        </div>
        <span className="flex items-center gap-2 text-sm text-secondary">
          <BadgeCheck aria-hidden="true" className="size-4 text-primary-700" />
          <strong className="numeric text-foreground">{query.data?.total ?? 0}</strong>{" "}
          brands
        </span>
      </section>
      {query.isPending ? (
        <LoadingState label="Loading brands…" />
      ) : query.isError ? (
        <ErrorState title="Brands could not be loaded" onRetry={() => query.refetch()} />
      ) : (
        <DataTable
          ariaLabel="Brands"
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
        title="Remove brand?"
        description={`This soft-deletes ${deleting?.name ?? "the brand"}. Brands linked to products cannot be removed.`}
        confirmLabel="Remove brand"
        destructive
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
      />
    </div>
  );
}
