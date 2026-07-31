import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { FilterBar, FilterField } from "@/components/ui/filter-bar";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { useHasPermission } from "@/features/auth/auth-store";
import { DeliveryAgentDrawer } from "@/features/orders/delivery-agent-drawer";
import { deleteDeliveryAgent, listDeliveryAgents } from "@/features/orders/orders-api";
import type { DeliveryAgent } from "@/features/orders/orders.data";
import { getApiErrorDetail } from "@/lib/api-errors";

export function DeliveryAgentsPage() {
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState<DeliveryAgent | null>(null);
  const deferred = useDeferredValue(search.trim());
  const canCreate = useHasPermission("delivery_agents.create");
  const canEdit = useHasPermission("delivery_agents.edit");
  const canDelete = useHasPermission("delivery_agents.delete");
  const queryClient = useQueryClient();
  const agents = useQuery({
    queryKey: ["delivery-agents", deferred],
    queryFn: () => listDeliveryAgents({ search: deferred || undefined }),
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
          <div className="flex justify-end gap-1">
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
              <Button
                variant="destructive"
                size="sm"
                aria-label={`Remove ${row.original.name}`}
                onClick={() => setDeleting(row.original)}
              >
                <Trash2 aria-hidden="true" />
              </Button>
            ) : null}
          </div>
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
          canCreate ? (
            <DeliveryAgentDrawer
              trigger={
                <Button>
                  <Plus aria-hidden="true" />
                  Create agent
                </Button>
              }
            />
          ) : null
        }
      />
      <FilterBar>
        <FilterField label="Search" htmlFor="agent-search">
          <div className="relative">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
            />
            <Input
              id="agent-search"
              className="pl-10"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Name, phone, or email"
            />
          </div>
        </FilterField>
      </FilterBar>
      <DataTable
        ariaLabel="Delivery agents"
        columns={columns}
        data={agents.data.items}
        getRowId={(agent) => agent.id}
        pageSize={10}
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
