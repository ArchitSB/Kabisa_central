import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Check, Eye, RotateCcw, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { FilterBar, FilterField } from "@/components/ui/filter-bar";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { listFeedback, setFeedbackHandled } from "@/features/customers/customers-api";
import type { CustomerFeedback } from "@/features/customers/types";
import { getApiErrorDetail } from "@/lib/api-errors";

const dateFormatter = new Intl.DateTimeFormat("en-TZ", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function CustomerFeedbackPage() {
  const [search, setSearch] = useState("");
  const [handled, setHandled] = useState("");
  const deferredSearch = useDeferredValue(search.trim());
  const queryClient = useQueryClient();
  const feedback = useQuery({
    queryKey: ["customer-feedback", deferredSearch, handled],
    queryFn: () =>
      listFeedback({
        search: deferredSearch || undefined,
        is_handled: handled === "" ? undefined : handled === "true",
      }),
  });
  const update = useMutation({
    mutationFn: ({ id, isHandled }: { id: string; isHandled: boolean }) =>
      setFeedbackHandled(id, isHandled),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["customer-feedback"] });
      toast.success("Feedback status updated");
    },
    onError: (error) =>
      toast.error("Feedback could not be updated", {
        description: getApiErrorDetail(error),
      }),
  });
  const columns = useMemo<ColumnDef<CustomerFeedback>[]>(
    () => [
      {
        id: "customer",
        header: "Customer",
        accessorFn: (item) => item.customer?.business_name,
        cell: ({ row }) =>
          row.original.customer ? (
            <Link
              to={`/customers/${row.original.customer.id}`}
              className="font-semibold hover:text-primary-800 hover:underline"
            >
              {row.original.customer.business_name}
            </Link>
          ) : (
            <span className="text-secondary">General</span>
          ),
      },
      {
        accessorKey: "subject",
        header: "Subject",
        cell: ({ row }) => (
          <span className="font-medium">{row.original.subject ?? "General feedback"}</span>
        ),
      },
      {
        accessorKey: "message",
        header: "Message",
        cell: ({ row }) => (
          <span className="block max-w-[420px] truncate text-secondary">
            {row.original.message}
          </span>
        ),
      },
      {
        accessorKey: "is_handled",
        header: "Status",
        cell: ({ row }) => (
          <StatusBadge
            label={row.original.is_handled ? "Handled" : "Needs action"}
            tone={row.original.is_handled ? "success" : "warning"}
          />
        ),
      },
      {
        accessorKey: "created_at",
        header: "Logged",
        cell: ({ row }) => (
          <span className="text-secondary">
            {dateFormatter.format(new Date(row.original.created_at))}
          </span>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        meta: { align: "right" },
        cell: ({ row }) => (
          <div className="flex justify-end gap-1">
            {row.original.customer ? (
              <Button asChild variant="ghost" size="sm">
                <Link to={`/customers/${row.original.customer.id}`}>
                  <Eye aria-hidden="true" />
                  View
                </Link>
              </Button>
            ) : null}
            <Button
              variant="secondary"
              size="sm"
              disabled={update.isPending}
              onClick={() =>
                update.mutate({ id: row.original.id, isHandled: !row.original.is_handled })
              }
            >
              {row.original.is_handled ? (
                <RotateCcw aria-hidden="true" />
              ) : (
                <Check aria-hidden="true" />
              )}
              {row.original.is_handled ? "Reopen" : "Mark handled"}
            </Button>
          </div>
        ),
      },
    ],
    [update],
  );

  if (feedback.isPending) return <LoadingState label="Loading feedback…" />;
  if (feedback.isError || !feedback.data) {
    return (
      <ErrorState title="Feedback could not be loaded" onRetry={() => feedback.refetch()} />
    );
  }
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Customers"
        title="Feedback"
        subtitle="Review service notes and customer requests across the Kabisa customer base."
      />
      <FilterBar className="[&>div:last-child]:xl:grid-cols-[minmax(260px,1fr)_220px_auto]">
        <FilterField label="Search" htmlFor="feedback-search">
          <div className="relative">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
            />
            <Input
              id="feedback-search"
              type="search"
              className="pl-10"
              placeholder="Customer, subject, message"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </FilterField>
        <FilterField label="Status" htmlFor="feedback-status">
          <select
            id="feedback-status"
            className="control-base w-full"
            value={handled}
            onChange={(event) => setHandled(event.target.value)}
          >
            <option value="">All feedback</option>
            <option value="false">Needs action</option>
            <option value="true">Handled</option>
          </select>
        </FilterField>
        <div className="flex items-end">
          <Button
            variant="secondary"
            onClick={() => {
              setSearch("");
              setHandled("");
            }}
          >
            <RotateCcw aria-hidden="true" />
            Reset
          </Button>
        </div>
      </FilterBar>
      <DataTable
        ariaLabel="Customer feedback"
        columns={columns}
        data={feedback.data.items}
        getRowId={(item) => item.id}
        pageSize={10}
        selectable={false}
      />
    </div>
  );
}
