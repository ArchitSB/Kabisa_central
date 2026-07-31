import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Building2, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  deleteWarehouse,
  listWarehouses,
  saveWarehouse,
} from "@/features/catalog/catalog-api";
import type { Warehouse } from "@/features/catalog/types";
import { useHasPermission } from "@/features/auth/auth-store";
import { WarehouseDrawer } from "@/features/warehouses/warehouse-drawer";
import { getApiErrorDetail } from "@/lib/api-errors";

export function WarehousesPage() {
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState<Warehouse | null>(null);
  const deferredSearch = useDeferredValue(search.trim());
  const canManage = useHasPermission("inventory.adjust");
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["warehouses", deferredSearch],
    queryFn: () => listWarehouses(deferredSearch),
  });
  const remove = useMutation({
    mutationFn: deleteWarehouse,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["warehouses"] });
      toast.success("Warehouse removed");
      setDeleting(null);
    },
    onError: (error) =>
      toast.error("Warehouse could not be removed", {
        description: getApiErrorDetail(error),
      }),
  });
  const toggle = useMutation({
    mutationFn: (warehouse: Warehouse) =>
      saveWarehouse(
        {
          name: warehouse.name,
          code: warehouse.code,
          address: warehouse.address,
          region: warehouse.region,
          is_primary: warehouse.is_primary,
          is_active: !warehouse.is_active,
        },
        warehouse.id,
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["warehouses"] }),
    onError: (error) =>
      toast.error("Status could not be changed", { description: getApiErrorDetail(error) }),
  });
  const columns = useMemo<ColumnDef<Warehouse>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Warehouse",
        cell: ({ row }) => (
          <div>
            <span className="block font-semibold">{row.original.name}</span>
            <span className="font-mono text-xs text-secondary">{row.original.code}</span>
          </div>
        ),
      },
      {
        accessorKey: "region",
        header: "Region",
        cell: ({ row }) => <span className="text-secondary">{row.original.region}</span>,
      },
      {
        accessorKey: "address",
        header: "Address",
        meta: { className: "max-w-[340px]" },
        cell: ({ row }) => (
          <span
            className="block max-w-[340px] truncate text-secondary"
            title={row.original.address}
          >
            {row.original.address}
          </span>
        ),
      },
      {
        accessorKey: "is_primary",
        header: "Priority",
        cell: ({ row }) =>
          row.original.is_primary ? (
            <StatusBadge label="Primary" tone="info" />
          ) : (
            <span className="text-secondary">Branch</span>
          ),
      },
      {
        accessorKey: "is_active",
        header: "Status",
        cell: ({ row }) =>
          canManage ? (
            <button
              type="button"
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
      ...(canManage
        ? [
            {
              id: "actions",
              header: "Actions",
              enableSorting: false,
              meta: { align: "right" as const },
              cell: ({ row }: { row: { original: Warehouse } }) => (
                <div className="flex justify-end gap-1">
                  <WarehouseDrawer
                    warehouse={row.original}
                    trigger={
                      <Button variant="ghost" size="sm">
                        <Pencil aria-hidden="true" />
                        Edit
                      </Button>
                    }
                  />
                  <Button
                    variant="destructive"
                    size="sm"
                    aria-label={`Delete ${row.original.name}`}
                    onClick={() => setDeleting(row.original)}
                  >
                    <Trash2 aria-hidden="true" />
                    Delete
                  </Button>
                </div>
              ),
            },
          ]
        : []),
    ],
    [canManage, toggle],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Inventory setup"
        title="Warehouses"
        subtitle="Manage physical stock locations across Kabisa’s distribution network."
        actions={
          canManage ? (
            <WarehouseDrawer
              trigger={
                <Button>
                  <Plus aria-hidden="true" />
                  Add warehouse
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
            placeholder="Search warehouses"
            aria-label="Search warehouses"
          />
        </div>
        <span className="flex items-center gap-2 text-sm text-secondary">
          <Building2 aria-hidden="true" className="size-4 text-primary-700" />
          <strong className="numeric text-foreground">{query.data?.total ?? 0}</strong>{" "}
          locations
        </span>
      </section>
      {query.isPending ? (
        <LoadingState label="Loading warehouses…" />
      ) : query.isError ? (
        <ErrorState
          title="Warehouses could not be loaded"
          onRetry={() => query.refetch()}
        />
      ) : (
        <DataTable
          ariaLabel="Warehouses"
          columns={columns}
          data={query.data.items}
          getRowId={(item) => item.id}
          selectable={false}
          pageSize={10}
        />
      )}
      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove warehouse?"
        description={`This soft-deletes ${deleting?.name ?? "the warehouse"}. Locations with inventory cannot be removed.`}
        confirmLabel="Remove warehouse"
        destructive
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
      />
    </div>
  );
}
