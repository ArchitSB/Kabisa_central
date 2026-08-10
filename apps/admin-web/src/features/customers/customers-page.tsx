import { useCallback, useMemo, useState } from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, Eye, Pencil, Plus, RotateCcw } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { BulkActionBar } from "@/components/ui/bulk-action-bar";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { FilterBar, FilterField, SearchInput } from "@/components/ui/filter-bar";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { DeleteRowAction, RowActions } from "@/components/ui/row-actions";
import { listPriceTiers } from "@/features/catalog/catalog-api";
import { useHasPermission } from "@/features/auth/auth-store";
import { CustomerDrawer } from "@/features/customers/customer-drawer";
import { BusinessTypeBadge, CustomerStatusBadge } from "@/features/customers/customer-ui";
import { businessTypeLabels } from "@/features/customers/customer-options";
import {
  deleteCustomer,
  listCustomers,
  type CustomerFilters,
} from "@/features/customers/customers-api";
import type { BusinessType, Customer } from "@/features/customers/types";
import { getApiErrorDetail } from "@/lib/api-errors";
import { bulkResultMessage, downloadSection, runBulkAction } from "@/lib/data-controls";
import { useDebouncedValue } from "@/lib/use-debounced-value";

const emptyFilters = {
  business_type: "",
  status: "",
  price_tier_id: "",
  payment_terms: "",
  region: "",
};
type Filters = typeof emptyFilters;

export function CustomersPage() {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [selected, setSelected] = useState<Customer[]>([]);
  const [deleting, setDeleting] = useState<Customer | null>(null);
  const [bulkDelete, setBulkDelete] = useState(false);
  const deferredSearch = useDebouncedValue(search.trim());
  const canCreate = useHasPermission("customers.create");
  const canEdit = useHasPermission("customers.edit");
  const canDelete = useHasPermission("customers.delete");
  const canVerify = useHasPermission("customers.verify");
  const canExport = useHasPermission("reports.export");
  const queryClient = useQueryClient();
  const params: CustomerFilters = {
    search: deferredSearch || undefined,
    business_type: filters.business_type || undefined,
    status: filters.status || undefined,
    price_tier_id: filters.price_tier_id || undefined,
    payment_terms: filters.payment_terms || undefined,
    region: filters.region || undefined,
  };
  const customers = useQuery({
    queryKey: ["customers", params],
    queryFn: () => listCustomers(params),
    placeholderData: keepPreviousData,
  });
  const tiers = useQuery({ queryKey: ["price-tiers"], queryFn: listPriceTiers });
  const remove = useMutation({
    mutationFn: (id: string) => deleteCustomer(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["customers"] });
      setDeleting(null);
      toast.success("Customer removed");
    },
    onError: (error) =>
      toast.error("Customer could not be removed", {
        description: getApiErrorDetail(error),
      }),
  });
  const bulk = useMutation({
    mutationFn: (action: string) =>
      runBulkAction("/customers/bulk", {
        ids: selected.map((item) => item.id),
        action,
      }),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["customers"] });
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
  const handleSelection = useCallback((rows: Customer[]) => setSelected(rows), []);
  const columns = useMemo<ColumnDef<Customer>[]>(
    () => [
      {
        accessorKey: "business_name",
        header: "Business",
        cell: ({ row }) => (
          <span>
            <Link
              to={`/customers/${row.original.id}`}
              className="block max-w-[260px] truncate font-semibold hover:text-primary-800 hover:underline"
            >
              {row.original.business_name}
            </Link>
            <span className="mt-0.5 block text-xs text-secondary">
              {row.original.region ?? "Region not recorded"}
            </span>
          </span>
        ),
      },
      {
        accessorKey: "business_type",
        header: "Type",
        cell: ({ row }) => <BusinessTypeBadge type={row.original.business_type} />,
      },
      {
        id: "contact",
        header: "Contact",
        accessorFn: (item) => item.contact_person,
        cell: ({ row }) => (
          <span>
            <span className="block font-medium">{row.original.contact_person ?? "—"}</span>
            <span className="block text-xs text-secondary">{row.original.phone}</span>
          </span>
        ),
      },
      {
        accessorKey: "email",
        header: "Email",
        cell: ({ row }) => (
          <span className="block max-w-[220px] truncate text-secondary">
            {row.original.email ?? "—"}
          </span>
        ),
      },
      {
        id: "tier",
        accessorFn: (item) => item.price_tier.code,
        header: "Price tier",
        cell: ({ row }) => (
          <span className="font-mono text-xs font-semibold text-primary-800">
            {row.original.price_tier.code}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => <CustomerStatusBadge status={row.original.status} />,
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        meta: { align: "right" },
        cell: ({ row }) => (
          <RowActions>
            <Button asChild variant="ghost" size="sm">
              <Link to={`/customers/${row.original.id}`}>
                <Eye aria-hidden="true" />
                View
              </Link>
            </Button>
            {canEdit ? (
              <CustomerDrawer
                customer={row.original}
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
                label={`Delete ${row.original.business_name}`}
                onClick={() => setDeleting(row.original)}
              />
            ) : null}
          </RowActions>
        ),
      },
    ],
    [canDelete, canEdit],
  );

  function handleBulkAction(action: string) {
    if (action === "delete") setBulkDelete(true);
    else if (action === "export") {
      void downloadSection(
        "/customers/export",
        { ids: selected.map((item) => item.id) },
        "kabisa-selected-customers.xlsx",
      ).catch((error) =>
        toast.error("Customers could not be downloaded", {
          description: getApiErrorDetail(error),
        }),
      );
    } else bulk.mutate(action);
  }

  async function downloadCustomers() {
    try {
      await downloadSection("/customers/export", params, "kabisa-customers.xlsx");
      toast.success("Customers downloaded");
    } catch (error) {
      toast.error("Customers could not be downloaded", {
        description: getApiErrorDetail(error),
      });
    }
  }

  if (customers.isPending) return <LoadingState label="Loading customers…" />;
  if (customers.isError || !customers.data) {
    return (
      <ErrorState
        title="Customers could not be loaded"
        onRetry={() => customers.refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Customers & verification"
        title="Customers"
        subtitle="Manage Kabisa’s B2B customer base, pricing tiers, verification readiness, and account status."
        actions={
          <>
            {canExport ? (
              <Button variant="secondary" onClick={downloadCustomers}>
                <Download aria-hidden="true" />
                Download
              </Button>
            ) : null}
            {canCreate ? (
              <CustomerDrawer
                trigger={
                  <Button>
                    <Plus aria-hidden="true" />
                    Create customer
                  </Button>
                }
              />
            ) : null}
          </>
        }
      />
      <FilterBar className="[&>div:last-child]:xl:grid-cols-4">
        <FilterField label="Search" htmlFor="customer-search">
          <SearchInput
            id="customer-search"
            value={search}
            placeholder="Name, contact, email, phone"
            onValueChange={setSearch}
          />
        </FilterField>
        <FilterField label="Business type" htmlFor="customer-type-filter">
          <select
            id="customer-type-filter"
            className="control-base w-full"
            value={filters.business_type}
            onChange={(event) =>
              setFilters((current) => ({ ...current, business_type: event.target.value }))
            }
          >
            <option value="">All types</option>
            {(Object.keys(businessTypeLabels) as BusinessType[]).map((type) => (
              <option key={type} value={type}>
                {businessTypeLabels[type]}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Status" htmlFor="customer-status-filter">
          <select
            id="customer-status-filter"
            className="control-base w-full"
            value={filters.status}
            onChange={(event) =>
              setFilters((current) => ({ ...current, status: event.target.value }))
            }
          >
            <option value="">All statuses</option>
            <option value="PENDING">Pending</option>
            <option value="UNDER_REVIEW">Under review</option>
            <option value="VERIFIED">Verified</option>
            <option value="REJECTED">Rejected</option>
            <option value="SUSPENDED">Suspended</option>
          </select>
        </FilterField>
        <FilterField label="Price tier" htmlFor="customer-tier-filter">
          <select
            id="customer-tier-filter"
            className="control-base w-full"
            value={filters.price_tier_id}
            onChange={(event) =>
              setFilters((current) => ({ ...current, price_tier_id: event.target.value }))
            }
          >
            <option value="">All tiers</option>
            {tiers.data?.items.map((tier) => (
              <option key={tier.id} value={tier.id}>
                {tier.name}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Payment terms" htmlFor="customer-payment-filter">
          <select
            id="customer-payment-filter"
            className="control-base w-full"
            value={filters.payment_terms}
            onChange={(event) =>
              setFilters((current) => ({ ...current, payment_terms: event.target.value }))
            }
          >
            <option value="">All terms</option>
            <option value="CASH">Cash</option>
            <option value="CREDIT">Credit</option>
          </select>
        </FilterField>
        <FilterField label="Region" htmlFor="customer-region-filter">
          <Input
            id="customer-region-filter"
            value={filters.region}
            placeholder="e.g. Mwanza"
            onChange={(event) =>
              setFilters((current) => ({ ...current, region: event.target.value }))
            }
          />
        </FilterField>
        <div className="flex items-end">
          <Button
            type="button"
            variant="secondary"
            className="w-full"
            onClick={() => {
              setSearch("");
              setFilters(emptyFilters);
            }}
          >
            <RotateCcw aria-hidden="true" />
            Reset
          </Button>
        </div>
      </FilterBar>
      <BulkActionBar
        selectedCount={selected.length}
        totalCount={customers.data.total}
        noun="customers"
        pending={bulk.isPending}
        showSort={false}
        actions={[
          ...(canVerify
            ? [
                { value: "submit", label: "Submit for review" },
                { value: "verify", label: "Verify doc-ready" },
                { value: "suspend", label: "Suspend customers" },
                { value: "reinstate", label: "Reinstate customers" },
              ]
            : []),
          ...(canDelete ? [{ value: "delete", label: "Delete customers" }] : []),
          ...(canExport ? [{ value: "export", label: "Export selected" }] : []),
        ]}
        onAction={handleBulkAction}
      />
      <DataTable
        ariaLabel="Kabisa customers"
        columns={columns}
        data={customers.data.items}
        getRowId={(customer) => customer.id}
        pageSize={10}
        selectable={canVerify || canDelete || canExport}
        onSelectionChange={handleSelection}
      />
      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove customer?"
        description={`${deleting?.business_name ?? "This customer"} will be soft-deleted and hidden from active workflows.`}
        confirmLabel="Remove customer"
        destructive
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
      />
      <ConfirmDialog
        open={bulkDelete}
        onOpenChange={setBulkDelete}
        title={`Remove ${selected.length} customers?`}
        description="Customers with open orders are skipped. Other selected customers are soft-deleted."
        confirmLabel="Remove selected"
        destructive
        pending={bulk.isPending}
        onConfirm={() => bulk.mutate("delete")}
      />
    </div>
  );
}
