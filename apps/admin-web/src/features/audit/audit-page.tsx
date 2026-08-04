import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Eye, FileClock, RotateCcw, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { FilterBar, FilterField } from "@/components/ui/filter-bar";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { getAuditOptions, listAuditLogs } from "@/features/audit/audit-api";
import type { AuditLog } from "@/features/audit/types";

const PAGE_SIZE = 20;

function readable(value: string) {
  return value
    .replaceAll("_", " ")
    .replaceAll(".", " · ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function displayTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AuditPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [actorId, setActorId] = useState("");
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selected, setSelected] = useState<AuditLog | null>(null);
  const deferredSearch = useDeferredValue(search.trim());
  const options = useQuery({
    queryKey: ["audit-options"],
    queryFn: getAuditOptions,
    staleTime: 60_000,
  });
  const query = useQuery({
    queryKey: [
      "audit-logs",
      page,
      deferredSearch,
      actorId,
      action,
      entityType,
      dateFrom,
      dateTo,
    ],
    queryFn: () =>
      listAuditLogs({
        page,
        page_size: PAGE_SIZE,
        search: deferredSearch || undefined,
        actor_id: actorId || undefined,
        action: action || undefined,
        entity_type: entityType || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
  });

  useEffect(
    () => setPage(1),
    [deferredSearch, actorId, action, entityType, dateFrom, dateTo],
  );

  const columns = useMemo<ColumnDef<AuditLog>[]>(
    () => [
      {
        accessorKey: "created_at",
        header: "Time",
        cell: ({ row }) => (
          <time dateTime={row.original.created_at} className="text-xs text-secondary">
            {displayTime(row.original.created_at)}
          </time>
        ),
      },
      {
        id: "actor",
        header: "Actor",
        cell: ({ row }) => (
          <div>
            <p className="font-semibold">
              {row.original.actor?.name ?? "System / unknown"}
            </p>
            {row.original.actor?.email ? (
              <p className="text-xs text-secondary">{row.original.actor.email}</p>
            ) : null}
          </div>
        ),
      },
      {
        accessorKey: "action",
        header: "Action",
        cell: ({ row }) => (
          <StatusBadge label={readable(row.original.action)} tone="info" />
        ),
      },
      {
        id: "entity",
        header: "Entity",
        cell: ({ row }) => (
          <div>
            <p className="font-medium">{readable(row.original.entity_type)}</p>
            <p className="max-w-48 truncate font-mono text-[11px] text-secondary">
              {row.original.entity_id ?? "No entity ID"}
            </p>
          </div>
        ),
      },
      {
        accessorKey: "ip_address",
        header: "IP address",
        cell: ({ row }) => (
          <span className="font-mono text-xs text-secondary">
            {row.original.ip_address ?? "Unavailable"}
          </span>
        ),
      },
      {
        id: "actions",
        header: "Details",
        enableSorting: false,
        meta: { align: "right" },
        cell: ({ row }) => (
          <Button variant="ghost" size="sm" onClick={() => setSelected(row.original)}>
            <Eye aria-hidden="true" />
            View
          </Button>
        ),
      },
    ],
    [],
  );

  function resetFilters() {
    setSearch("");
    setActorId("");
    setAction("");
    setEntityType("");
    setDateFrom("");
    setDateTo("");
  }

  const pageCount = Math.ceil((query.data?.total ?? 0) / PAGE_SIZE);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Governance"
        title="Audit log"
        subtitle="Review immutable records of authentication, regulatory, stock, order, payment, delivery, pricing, and access-management actions."
      />

      <FilterBar title="Audit filters">
        <FilterField
          label="Search"
          htmlFor="audit-search"
          className="md:col-span-2 xl:col-span-1"
        >
          <div className="relative">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
            />
            <Input
              id="audit-search"
              type="search"
              className="pl-10"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Action, actor, entity, or ID"
            />
          </div>
        </FilterField>
        <FilterField label="Actor" htmlFor="audit-actor">
          <select
            id="audit-actor"
            className="control-base w-full"
            value={actorId}
            onChange={(event) => setActorId(event.target.value)}
          >
            <option value="">All actors</option>
            {options.data?.actors.map((actor) => (
              <option key={actor.id} value={actor.id}>
                {actor.name}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Action" htmlFor="audit-action">
          <select
            id="audit-action"
            className="control-base w-full"
            value={action}
            onChange={(event) => setAction(event.target.value)}
          >
            <option value="">All actions</option>
            {options.data?.actions.map((option) => (
              <option key={option.value} value={option.value}>
                {readable(option.label)}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Entity" htmlFor="audit-entity">
          <select
            id="audit-entity"
            className="control-base w-full"
            value={entityType}
            onChange={(event) => setEntityType(event.target.value)}
          >
            <option value="">All entity types</option>
            {options.data?.entity_types.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="From" htmlFor="audit-date-from">
          <Input
            id="audit-date-from"
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
          />
        </FilterField>
        <FilterField label="To" htmlFor="audit-date-to">
          <Input
            id="audit-date-to"
            type="date"
            min={dateFrom || undefined}
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
          />
        </FilterField>
        <Button type="button" variant="secondary" onClick={resetFilters}>
          <RotateCcw aria-hidden="true" />
          Reset
        </Button>
      </FilterBar>

      {query.isLoading ? <LoadingState label="Loading audit records…" /> : null}
      {query.isError ? (
        <ErrorState
          title="Audit records could not be loaded"
          onRetry={() => query.refetch()}
        />
      ) : null}
      {query.data && query.data.total === 0 ? (
        <EmptyState
          icon={FileClock}
          title="No audit records match"
          description="Adjust the filters or perform a protected administrative action."
        />
      ) : null}
      {query.data && query.data.total > 0 ? (
        <>
          <DataTable
            ariaLabel="Administrative audit records"
            columns={columns}
            data={query.data.items}
            getRowId={(row) => row.id}
            selectable={false}
            showPagination={false}
          />
          <Pagination
            page={page}
            pageCount={pageCount}
            canPrevious={page > 1}
            canNext={page < pageCount}
            onPrevious={() => setPage((current) => Math.max(1, current - 1))}
            onNext={() => setPage((current) => Math.min(pageCount, current + 1))}
          />
        </>
      ) : null}

      <Drawer open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)}>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Audit record</DrawerTitle>
            <DrawerDescription>
              Immutable request context and change metadata for this action.
            </DrawerDescription>
          </DrawerHeader>
          {selected ? (
            <div className="space-y-5 px-6 py-6">
              <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-semibold text-secondary">Action</dt>
                  <dd className="mt-1 font-medium">{readable(selected.action)}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-secondary">Recorded</dt>
                  <dd className="mt-1">{displayTime(selected.created_at)}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-secondary">Actor</dt>
                  <dd className="mt-1">{selected.actor?.name ?? "System / unknown"}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-secondary">IP address</dt>
                  <dd className="mt-1 font-mono text-xs">
                    {selected.ip_address ?? "Unavailable"}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs font-semibold text-secondary">Entity</dt>
                  <dd className="mt-1 break-all font-mono text-xs">
                    {selected.entity_type} · {selected.entity_id ?? "No entity ID"}
                  </dd>
                </div>
              </dl>
              <div>
                <h3 className="text-sm font-semibold">Change context</h3>
                <pre className="scrollbar-subtle mt-2 max-h-[420px] overflow-auto rounded-control border border-border bg-[#FBFCFB] p-4 text-xs leading-5 text-foreground">
                  {JSON.stringify(selected.changes ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          ) : null}
          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Close
              </Button>
            </DrawerClose>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>
    </div>
  );
}
