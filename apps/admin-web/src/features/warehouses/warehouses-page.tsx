import { useCallback, useMemo, useState } from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Building2, CheckCircle2, Download, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";

import { BulkActionBar } from "@/components/ui/bulk-action-bar";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { SearchInput } from "@/components/ui/filter-bar";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { DeleteRowAction, RowActions } from "@/components/ui/row-actions";
import {
  deleteWarehouse,
  listWarehouses,
  saveWarehouse,
  setPrimaryWarehouse,
} from "@/features/catalog/catalog-api";
import type { Warehouse } from "@/features/catalog/types";
import { useHasPermission } from "@/features/auth/auth-store";
import { WarehouseDrawer } from "@/features/warehouses/warehouse-drawer";
import { getApiErrorDetail } from "@/lib/api-errors";
import { bulkResultMessage, downloadSection, runBulkAction } from "@/lib/data-controls";
import { useDebouncedValue } from "@/lib/use-debounced-value";

export function WarehousesPage() {
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState<Warehouse | null>(null);
  const [selected, setSelected] = useState<Warehouse[]>([]);
  const [bulkDelete, setBulkDelete] = useState(false);
  const deferredSearch = useDebouncedValue(search.trim());
  const canManage = useHasPermission("inventory.adjust");
  const canExport = useHasPermission("reports.export");
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["warehouses", deferredSearch],
    queryFn: () => listWarehouses(deferredSearch),
    placeholderData: keepPreviousData,
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
  const makePrimary = useMutation({
    mutationFn: setPrimaryWarehouse,
    onSuccess: async (warehouse) => {
      await queryClient.invalidateQueries({ queryKey: ["warehouses"] });
      toast.success(`${warehouse.name} is now primary`);
    },
    onError: (error) =>
      toast.error("Primary warehouse could not be changed", {
        description: getApiErrorDetail(error),
      }),
  });
  const bulk = useMutation({
    mutationFn: (action: string) =>
      runBulkAction("/warehouses/bulk", {
        ids: selected.map((item) => item.id),
        action,
      }),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["warehouses"] });
      setSelected([]);
      setBulkDelete(false);
      const message = bulkResultMessage(result);
      if (result.skipped || result.failed)
        toast.warning(message.title, { description: message.description });
      else toast.success(message.title);
    },
    onError: (error) =>
      toast.error("Bulk action failed", { description: getApiErrorDetail(error) }),
  });
  const handleSelection = useCallback((rows: Warehouse[]) => setSelected(rows), []);
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
      ...(canManage
        ? [
            {
              id: "actions",
              header: "Actions",
              enableSorting: false,
              meta: { align: "right" as const },
              cell: ({ row }: { row: { original: Warehouse } }) => (
                <RowActions>
                  {!row.original.is_primary ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => makePrimary.mutate(row.original.id)}
                    >
                      <CheckCircle2 aria-hidden="true" />
                      Set primary
                    </Button>
                  ) : null}
                  <WarehouseDrawer
                    warehouse={row.original}
                    trigger={
                      <Button variant="ghost" size="sm">
                        <Pencil aria-hidden="true" />
                        Edit
                      </Button>
                    }
                  />
                  <DeleteRowAction
                    label={`Delete ${row.original.name}`}
                    onClick={() => setDeleting(row.original)}
                  />
                </RowActions>
              ),
            },
          ]
        : []),
    ],
    [canManage, makePrimary, toggle],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Inventory setup"
        title="Warehouses"
        subtitle="Manage physical stock locations across Kabisa’s distribution network."
        actions={
          <>
            {canExport ? (
              <Button
                variant="secondary"
                onClick={() =>
                  downloadSection(
                    "/warehouses/export",
                    { search: deferredSearch || undefined },
                    "kabisa-warehouses.xlsx",
                  ).catch((error) =>
                    toast.error("Warehouses could not be downloaded", {
                      description: getApiErrorDetail(error),
                    }),
                  )
                }
              >
                <Download aria-hidden="true" />
                Download
              </Button>
            ) : null}
            {canManage ? (
              <WarehouseDrawer
                trigger={
                  <Button>
                    <Plus aria-hidden="true" />
                    Add warehouse
                  </Button>
                }
              />
            ) : null}
          </>
        }
      />
      <section className="surface-card flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full sm:max-w-md">
          <SearchInput
            value={search}
            onValueChange={setSearch}
            placeholder="Search warehouses"
            ariaLabel="Search warehouses"
          />
        </div>
        <span className="flex items-center gap-2 text-sm text-secondary">
          <Building2 aria-hidden="true" className="size-4 text-primary-700" />
          <strong className="numeric text-foreground">{query.data?.total ?? 0}</strong>{" "}
          locations
        </span>
      </section>
      {canManage || canExport ? (
        <BulkActionBar
          selectedCount={selected.length}
          totalCount={query.data?.total ?? 0}
          noun="warehouses"
          showSort={false}
          pending={bulk.isPending || remove.isPending}
          actions={[
            ...(canManage
              ? [
                  { value: "activate", label: "Activate warehouses" },
                  { value: "deactivate", label: "Deactivate warehouses" },
                  { value: "delete", label: "Delete warehouses" },
                ]
              : []),
            ...(canExport ? [{ value: "export", label: "Export selected" }] : []),
          ]}
          onAction={(action) => {
            if (action === "delete") setBulkDelete(true);
            else if (action === "export") {
              void downloadSection(
                "/warehouses/export",
                { ids: selected.map((item) => item.id) },
                "kabisa-selected-warehouses.xlsx",
              ).catch((error) =>
                toast.error("Warehouses could not be downloaded", {
                  description: getApiErrorDetail(error),
                }),
              );
            } else bulk.mutate(action);
          }}
        />
      ) : null}
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
          selectable={canManage || canExport}
          onSelectionChange={handleSelection}
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
      <ConfirmDialog
        open={bulkDelete}
        onOpenChange={setBulkDelete}
        title={`Remove ${selected.length} warehouses?`}
        description="Primary locations and warehouses with live inventory or open orders are skipped."
        confirmLabel="Remove selected"
        destructive
        pending={bulk.isPending}
        onConfirm={() => bulk.mutate("delete")}
      />
    </div>
  );
}
