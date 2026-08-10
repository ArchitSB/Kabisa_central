import { useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { AlertCircle, LoaderCircle, Pencil, Plus, UsersRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { SearchInput } from "@/components/ui/filter-bar";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { AdminUserDrawer } from "@/features/admin-users/admin-user-drawer";
import { type AdminUser, listAdminUsers } from "@/features/admin-users/admin-users-api";
import { useHasPermission } from "@/features/auth/auth-store";
import { formatRoleName, getInitials } from "@/lib/utils";
import { useDebouncedValue } from "@/lib/use-debounced-value";

const dateFormatter = new Intl.DateTimeFormat("en-TZ", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function AdminUsersPage() {
  const [search, setSearch] = useState("");
  const deferredSearch = useDebouncedValue(search.trim());
  const canCreate = useHasPermission("admin_users.create");
  const canEdit = useHasPermission("admin_users.edit");
  const query = useQuery({
    queryKey: ["admin-users", deferredSearch],
    queryFn: () => listAdminUsers(deferredSearch),
    placeholderData: keepPreviousData,
  });
  const columns = useMemo<ColumnDef<AdminUser>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Administrator",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-800">
              {getInitials(row.original.name)}
            </span>
            <span>
              <span className="block font-semibold">{row.original.name}</span>
              <span className="block text-xs text-secondary">{row.original.email}</span>
            </span>
          </div>
        ),
      },
      {
        accessorFn: (user) => user.role.name,
        id: "role",
        header: "Role",
        cell: ({ row }) => (
          <StatusBadge
            label={
              row.original.role.name === "super_admin"
                ? "Super Admin · Developer"
                : formatRoleName(row.original.role.name)
            }
            tone={row.original.role.name === "super_admin" ? "info" : "neutral"}
          />
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
        accessorKey: "last_login_at",
        header: "Last sign-in",
        cell: ({ row }) => (
          <span className="text-sm text-secondary">
            {row.original.last_login_at
              ? dateFormatter.format(new Date(row.original.last_login_at))
              : "Never"}
          </span>
        ),
      },
      ...(canEdit
        ? [
            {
              id: "actions",
              header: "Actions",
              enableSorting: false,
              meta: { align: "right" as const },
              cell: ({ row }: { row: { original: AdminUser } }) => (
                <AdminUserDrawer
                  user={row.original}
                  trigger={
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      aria-label={`Edit ${row.original.name}`}
                    >
                      <Pencil aria-hidden="true" />
                      Edit
                    </Button>
                  }
                />
              ),
            },
          ]
        : []),
    ],
    [canEdit],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Access management"
        title="Admin users"
        subtitle="Create operational accounts, assign one role, and control sign-in access."
        actions={
          canCreate ? (
            <AdminUserDrawer
              trigger={
                <Button>
                  <Plus aria-hidden="true" />
                  Add administrator
                </Button>
              }
            />
          ) : null
        }
      />

      <section className="surface-card flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full sm:max-w-md">
          <SearchInput
            value={search}
            onValueChange={setSearch}
            placeholder="Search name or email"
            ariaLabel="Search administrators"
          />
        </div>
        <div className="flex items-center gap-2 text-sm text-secondary">
          <UsersRound aria-hidden="true" className="size-4 text-primary-700" />
          <span className="numeric font-semibold text-foreground">
            {query.data?.total ?? 0}
          </span>
          administrators
        </div>
      </section>

      {query.isPending ? (
        <div
          className="surface-card flex min-h-64 items-center justify-center"
          role="status"
        >
          <LoaderCircle
            aria-hidden="true"
            className="size-6 animate-spin text-primary-700"
          />
          <span className="ml-3 text-sm font-medium text-secondary">
            Loading administrators…
          </span>
        </div>
      ) : query.isError ? (
        <div className="surface-card flex min-h-64 flex-col items-center justify-center px-6 text-center">
          <AlertCircle aria-hidden="true" className="size-7 text-danger" />
          <p className="mt-3 font-semibold">Administrators could not be loaded</p>
          <p className="mt-1 text-sm text-secondary">
            Check the API connection and try again.
          </p>
          <Button variant="secondary" className="mt-5" onClick={() => query.refetch()}>
            Try again
          </Button>
        </div>
      ) : (
        <DataTable
          ariaLabel="Admin users"
          columns={columns}
          data={query.data.items}
          getRowId={(user) => user.id}
          pageSize={10}
          selectable={false}
        />
      )}
    </div>
  );
}
