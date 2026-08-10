import { useCallback, useMemo, useState } from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";

import { BulkActionBar } from "@/components/ui/bulk-action-bar";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { FilterBar, FilterField, SearchInput } from "@/components/ui/filter-bar";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { DeleteRowAction, RowActions } from "@/components/ui/row-actions";
import { useHasPermission } from "@/features/auth/auth-store";
import { DeliveryAgentDrawer } from "@/features/orders/delivery-agent-drawer";
import { deleteDeliveryAgent, listDeliveryAgents } from "@/features/orders/orders-api";
import type { DeliveryAgent } from "@/features/orders/orders.data";
import { getApiErrorDetail } from "@/lib/api-errors";
import { bulkResultMessage, downloadSection, runBulkAction } from "@/lib/data-controls";
import { useDebouncedValue } from "@/lib/use-debounced-value";

export function DeliveryAgentsPage() {
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState<DeliveryAgent | null>(null);
  const [selected, setSelected] = useState<DeliveryAgent[]>([]);
  const [bulkDelete, setBulkDelete] = useState(false);
  const deferred = useDebouncedValue(search.trim());
  const canCreate = useHasPermission("delivery_agents.create");
  const canEdit = useHasPermission("delivery_agents.edit");
  const canDelete = useHasPermission("delivery_agents.delete");
  const canExport = useHasPermission("reports.export");
  const queryClient = useQueryClient();
  const agents = useQuery({
    queryKey: ["delivery-agents", deferred],
    queryFn: () => listDeliveryAgents({ search: deferred || undefined }),
    placeholderData: keepPreviousData,
  });
  const remove = useMutation({
    mutationFn: deleteDeliveryAgent,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["delivery-agents"] });
      setDeleting(null);
      toast.success("Delivery agent removed");
    },
    onError: (error) =>
      toast.error("Delivery agent could not be removed", {
        description: getApiErrorDetail(error),
      }),
  });
  const bulk = useMutation({
    mutationFn: (action: string) =>
      runBulkAction("/delivery-agents/bulk", {
        ids: selected.map((item) => item.id),
        action,
      }),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["delivery-agents"] });
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
  const handleSelection = useCallback((rows: DeliveryAgent[]) => setSelected(rows), []);
  const columns = useMemo<ColumnDef<DeliveryAgent>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Agent",
        cell: ({ row }) => (
          <div>
            <strong>{row.original.name}</strong>
            <span className="block text-xs text-secondary">
              {row.original.email ?? "No email"}
            </span>
          </div>
        ),
      },
      { accessorKey: "phone", header: "Phone" },
      {
        accessorKey: "vehicle_type",
        header: "Vehicle",
        cell: ({ row }) => row.original.vehicle_type?.replaceAll("_", " ") ?? "—",
      },
      {
        accessorKey: "address",
        header: "Address",
        cell: ({ row }) => (
          <span className="block max-w-[240px] truncate text-secondary">
            {row.original.address ?? "—"}
          </span>
        ),
      },
      {
        accessorKey: "is_active",
        header: "Status",
        cell: ({ row }) => (
          <StatusBadge
            label={row.original.is_active ? "Active" : "Inactive"}
            tone={row.original.is_active ? "success" : "neutral"}
          />
        ),
      },
      {
        id: "actions",
        header: "Actions",
        meta: { align: "right" },
        cell: ({ row }) => (
          <RowActions>
            {canEdit ? (
              <DeliveryAgentDrawer
                agent={row.original}
                trigger={
                  <Button variant="ghost" size="sm">
                    <Pencil aria-hidden="true" />
                    Edit
                  </Button>
                }
              />
            ) : null}
            {canDelete ? (
              <DeleteRowAction
                label={`Remove ${row.original.name}`}
                onClick={() => setDeleting(row.original)}
              />
            ) : null}
          </RowActions>
        ),
      },
    ],
    [canDelete, canEdit],
  );
  if (agents.isPending) return <LoadingState label="Loading delivery agents…" />;
  if (agents.isError || !agents.data)
    return (
      <ErrorState
        title="Delivery agents could not be loaded"
        onRetry={() => agents.refetch()}
      />
    );
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Orders & delivery"
        title="Delivery agents"
        subtitle="Manage Kabisa’s motorcycle, van, and truck delivery team."
        actions={
          <>
            {canExport ? (
              <Button
                variant="secondary"
                onClick={() =>
                  downloadSection(
                    "/delivery-agents/export",
                    { search: deferred || undefined },
                    "kabisa-delivery-agents.xlsx",
                  ).catch((error) =>
                    toast.error("Delivery agents could not be downloaded", {
                      description: getApiErrorDetail(error),
                    }),
                  )
                }
              >
                <Download aria-hidden="true" />
                Download
              </Button>
            ) : null}
            {canCreate ? (
              <DeliveryAgentDrawer
                trigger={
                  <Button>
                    <Plus aria-hidden="true" />
                    Create agent
                  </Button>
                }
              />
            ) : null}
          </>
        }
      />
      <FilterBar>
        <FilterField label="Search" htmlFor="agent-search">
          <SearchInput
            id="agent-search"
            value={search}
            onValueChange={setSearch}
            placeholder="Name, phone, or email"
          />
        </FilterField>
      </FilterBar>
      {canEdit || canDelete || canExport ? (
        <BulkActionBar
          selectedCount={selected.length}
          totalCount={agents.data.total}
          noun="agents"
          showSort={false}
          pending={bulk.isPending || remove.isPending}
          actions={[
            ...(canEdit
              ? [
                  { value: "activate", label: "Activate agents" },
                  { value: "deactivate", label: "Deactivate agents" },
                ]
              : []),
            ...(canDelete ? [{ value: "delete", label: "Delete agents" }] : []),
            ...(canExport ? [{ value: "export", label: "Export selected" }] : []),
          ]}
          onAction={(action) => {
            if (action === "delete") setBulkDelete(true);
            else if (action === "export") {
              void downloadSection(
                "/delivery-agents/export",
                { ids: selected.map((item) => item.id) },
                "kabisa-selected-delivery-agents.xlsx",
              ).catch((error) =>
                toast.error("Delivery agents could not be downloaded", {
                  description: getApiErrorDetail(error),
                }),
              );
            } else bulk.mutate(action);
          }}
        />
      ) : null}
      <DataTable
        ariaLabel="Delivery agents"
        columns={columns}
        data={agents.data.items}
        getRowId={(agent) => agent.id}
        pageSize={10}
        selectable={canEdit || canDelete || canExport}
        onSelectionChange={handleSelection}
      />
      <ConfirmDialog
        open={bulkDelete}
        onOpenChange={setBulkDelete}
        title={`Remove ${selected.length} delivery agents?`}
        description="Agents with active deliveries are skipped; others are soft-deleted."
        confirmLabel="Remove selected"
        destructive
        pending={bulk.isPending}
        onConfirm={() => bulk.mutate("delete")}
      />
      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove delivery agent?"
        description="The agent will be deactivated and hidden from future assignment."
        confirmLabel="Remove"
        destructive
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
      />
    </div>
  );
}
