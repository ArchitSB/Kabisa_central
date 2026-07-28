import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ChevronDown,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  Pencil,
  Plus,
  ShieldCheck,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { useHasPermission } from "@/features/auth/auth-store";
import type { Permission } from "@/features/auth/types";
import { RoleDrawer } from "@/features/roles/role-drawer";
import { listRoles } from "@/features/roles/roles-api";
import { formatRoleName } from "@/lib/utils";

export function RolesPage() {
  const canManage = useHasPermission("roles.manage");
  const query = useQuery({
    queryKey: ["roles"],
    queryFn: listRoles,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Access management"
        title="Roles & permissions"
        subtitle="Review the effective permission set for each role. System roles stay fixed; custom roles can be tailored."
        actions={
          canManage ? (
            <RoleDrawer
              trigger={
                <Button>
                  <Plus aria-hidden="true" />
                  Create custom role
                </Button>
              }
            />
          ) : null
        }
      />

      {query.isPending ? (
        <div
          className="surface-card flex min-h-64 items-center justify-center"
          role="status"
        >
          <LoaderCircle
            aria-hidden="true"
            className="size-6 animate-spin text-primary-700"
          />
          <span className="ml-3 text-sm font-medium text-secondary">Loading roles…</span>
        </div>
      ) : query.isError ? (
        <div className="surface-card flex min-h-64 flex-col items-center justify-center px-6 text-center">
          <AlertCircle aria-hidden="true" className="size-7 text-danger" />
          <p className="mt-3 font-semibold">Roles could not be loaded</p>
          <p className="mt-1 text-sm text-secondary">
            Check the API connection and try again.
          </p>
          <Button variant="secondary" className="mt-5" onClick={() => query.refetch()}>
            Try again
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {query.data.items.map((role) => {
            const groups = groupPermissions(role.permissions);
            return (
              <article key={role.id} className="surface-card overflow-hidden">
                <div className="flex items-start gap-4 border-b border-border p-5">
                  <span className="flex size-11 shrink-0 items-center justify-center rounded-[12px] bg-primary-100 text-primary-800">
                    {role.is_system ? (
                      <ShieldCheck aria-hidden="true" className="size-5" />
                    ) : (
                      <KeyRound aria-hidden="true" className="size-5" />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-display text-xl font-semibold tracking-tight">
                        {formatRoleName(role.name)}
                      </h2>
                      <StatusBadge
                        label={role.is_system ? "System role" : "Custom role"}
                        tone={role.is_system ? "info" : "neutral"}
                      />
                    </div>
                    <p className="mt-1 text-sm leading-6 text-secondary">
                      {role.description}
                    </p>
                  </div>
                  {canManage && !role.is_system ? (
                    <RoleDrawer
                      role={role}
                      trigger={
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          aria-label={`Edit ${formatRoleName(role.name)}`}
                        >
                          <Pencil aria-hidden="true" />
                          Edit
                        </Button>
                      }
                    />
                  ) : (
                    <span
                      className="flex size-8 shrink-0 items-center justify-center rounded-full bg-neutral-surface text-neutral"
                      title="System roles are read-only"
                    >
                      <LockKeyhole aria-hidden="true" className="size-3.5" />
                    </span>
                  )}
                </div>

                <details className="group">
                  <summary className="flex min-h-12 items-center justify-between gap-3 px-5 py-3 text-sm font-semibold text-foreground transition-colors duration-micro hover:bg-[var(--row-hover)]">
                    <span>
                      <span className="numeric">{role.permissions.length}</span> permissions
                      across <span className="numeric">{Object.keys(groups).length}</span>{" "}
                      groups
                    </span>
                    <ChevronDown
                      aria-hidden="true"
                      className="size-4 text-secondary transition-transform duration-standard group-open:rotate-180"
                    />
                  </summary>
                  <div className="space-y-5 border-t border-border bg-[#FBFCFB] p-5">
                    {Object.entries(groups).map(([group, permissions]) => (
                      <section key={group} aria-label={`${group} permissions`}>
                        <h3 className="text-[11px] font-bold uppercase tracking-[0.1em] text-primary-700">
                          {group}
                        </h3>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {permissions.map((permission) => (
                            <span
                              key={permission.id}
                              className="rounded-full border border-border bg-surface px-2.5 py-1 font-mono text-[10px] font-semibold text-secondary"
                              title={permission.description}
                            >
                              {permission.code}
                            </span>
                          ))}
                        </div>
                      </section>
                    ))}
                  </div>
                </details>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

function groupPermissions(permissions: Permission[]): Record<string, Permission[]> {
  return permissions.reduce<Record<string, Permission[]>>((groups, permission) => {
    (groups[permission.group] ??= []).push(permission);
    return groups;
  }, {});
}
