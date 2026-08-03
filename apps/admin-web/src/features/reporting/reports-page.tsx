import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { FilterBar, FilterField } from "@/components/ui/filter-bar";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tabs } from "@/components/ui/tabs";
import { useHasPermission } from "@/features/auth/auth-store";
import { orderStatusLabels, paymentStatusLabels } from "@/features/orders/orders.data";
import {
  downloadReport,
  getInventoryReport,
  getProductsReport,
  getReceivablesReport,
  getReportOptions,
  getSalesReport,
  type ReportFilters,
  type ReportKind,
} from "@/features/reporting/reporting-api";
import type {
  InventoryReport,
  ProductsReport,
  ReceivablesReport,
  SalesReport,
} from "@/features/reporting/types";
import { formatMoney } from "@/lib/utils";

type ReportData = SalesReport | ProductsReport | ReceivablesReport | InventoryReport;
type DisplayRow = {
  id: string;
  reference: string;
  primary: string;
  secondary?: string;
  warehouse?: string;
  date?: string;
  status?: string;
  payment?: string;
  quantity?: number;
  amount?: number;
  collected?: number;
  balance?: number;
  tax?: number;
  discount?: number;
  age?: string;
  expiry?: string;
  low?: boolean;
  expiring?: boolean;
  dead?: boolean;
};

const reportLabels: Record<ReportKind, string> = {
  sales: "Sales",
  products: "Products",
  receivables: "Receivables",
  inventory: "Inventory",
};

async function reportQuery(kind: ReportKind, filters: ReportFilters): Promise<ReportData> {
  if (kind === "sales") return await getSalesReport(filters);
  if (kind === "products") return await getProductsReport(filters);
  if (kind === "receivables") return await getReceivablesReport(filters);
  return await getInventoryReport(filters);
}

function normalizedRows(kind: ReportKind, data: ReportData): DisplayRow[] {
  if (kind === "sales") {
    return (data as SalesReport).items.map((row) => ({
      id: row.order_id,
      reference: row.order_number,
      primary: row.customer_name,
      warehouse: row.warehouse_name,
      date: row.order_date,
      status: orderStatusLabels[row.status],
      payment: paymentStatusLabels[row.payment_status],
      amount: row.total_amount,
      collected: row.collected_amount,
      balance: row.balance_due,
    }));
  }
  if (kind === "products") {
    return (data as ProductsReport).items.map((row) => ({
      id: row.product_id,
      reference: row.sku,
      primary: row.name,
      secondary: `${row.brand ?? "No brand"} · ${row.category}`,
      quantity: row.quantity_sold,
      amount: row.revenue,
      tax: row.tax,
      discount: row.discount,
    }));
  }
  if (kind === "receivables") {
    return (data as ReceivablesReport).items.map((row) => ({
      id: row.order_id,
      reference: row.order_number,
      primary: row.customer_name,
      date: row.order_date,
      payment: paymentStatusLabels[row.payment_status],
      amount: row.total_amount,
      collected: row.collected_amount,
      balance: row.balance_due,
      age: `${row.age_days} days · ${row.aging_bucket}`,
    }));
  }
  return (data as InventoryReport).items.map((row) => ({
    id: row.batch_id,
    reference: row.sku,
    primary: row.product_name,
    secondary: row.batch_number,
    warehouse: row.warehouse_name,
    quantity: row.on_hand,
    amount: row.stock_value,
    expiry: row.expiry_date,
    low: row.low_stock,
    expiring: row.expiring_soon,
    dead: row.dead_stock,
  }));
}

function columns(kind: ReportKind, currency: string): ColumnDef<DisplayRow>[] {
  const identity: ColumnDef<DisplayRow>[] = [
    {
      accessorKey: "reference",
      header: kind === "inventory" || kind === "products" ? "SKU" : "Order",
      cell: ({ row }) => (
        <span className="font-mono text-xs font-semibold text-primary-700">
          {row.original.reference}
        </span>
      ),
    },
    {
      accessorKey: "primary",
      header: kind === "sales" || kind === "receivables" ? "Customer" : "Product",
      cell: ({ row }) => (
        <div>
          <p className="font-semibold">{row.original.primary}</p>
          {row.original.secondary ? (
            <p className="mt-0.5 text-xs text-secondary">{row.original.secondary}</p>
          ) : null}
        </div>
      ),
    },
  ];
  if (kind === "sales") {
    return [
      ...identity,
      { accessorKey: "warehouse", header: "Warehouse" },
      {
        accessorKey: "date",
        header: "Date",
        cell: ({ row }) => new Date(row.original.date ?? "").toLocaleDateString("en-TZ"),
      },
      {
        accessorKey: "payment",
        header: "Payment",
        cell: ({ row }) => (
          <StatusBadge
            label={row.original.payment ?? "—"}
            tone={row.original.payment === "Paid" ? "success" : "warning"}
          />
        ),
      },
      {
        accessorKey: "amount",
        header: "Total",
        meta: { align: "right" },
        cell: ({ row }) => (
          <span className="numeric font-semibold">
            {formatMoney(row.original.amount ?? 0, currency)}
          </span>
        ),
      },
      {
        accessorKey: "collected",
        header: "Collected",
        meta: { align: "right" },
        cell: ({ row }) => (
          <span className="numeric">
            {formatMoney(row.original.collected ?? 0, currency)}
          </span>
        ),
      },
      {
        accessorKey: "balance",
        header: "Balance",
        meta: { align: "right" },
        cell: ({ row }) => (
          <span className="numeric font-semibold text-warning">
            {formatMoney(row.original.balance ?? 0, currency)}
          </span>
        ),
      },
    ];
  }
  if (kind === "products") {
    return [
      ...identity,
      { accessorKey: "quantity", header: "Qty sold", meta: { align: "right" } },
      {
        accessorKey: "discount",
        header: "Discount",
        meta: { align: "right" },
        cell: ({ row }) => formatMoney(row.original.discount ?? 0, currency),
      },
      {
        accessorKey: "tax",
        header: "Tax",
        meta: { align: "right" },
        cell: ({ row }) => formatMoney(row.original.tax ?? 0, currency),
      },
      {
        accessorKey: "amount",
        header: "Revenue",
        meta: { align: "right" },
        cell: ({ row }) => (
          <span className="numeric font-semibold">
            {formatMoney(row.original.amount ?? 0, currency)}
          </span>
        ),
      },
    ];
  }
  if (kind === "receivables") {
    return [
      ...identity,
      { accessorKey: "age", header: "Aging" },
      {
        accessorKey: "payment",
        header: "Payment",
        cell: ({ row }) => (
          <StatusBadge label={row.original.payment ?? "—"} tone="warning" />
        ),
      },
      {
        accessorKey: "amount",
        header: "Order total",
        meta: { align: "right" },
        cell: ({ row }) => formatMoney(row.original.amount ?? 0, currency),
      },
      {
        accessorKey: "collected",
        header: "Collected",
        meta: { align: "right" },
        cell: ({ row }) => formatMoney(row.original.collected ?? 0, currency),
      },
      {
        accessorKey: "balance",
        header: "Outstanding",
        meta: { align: "right" },
        cell: ({ row }) => (
          <span className="numeric font-semibold text-warning">
            {formatMoney(row.original.balance ?? 0, currency)}
          </span>
        ),
      },
    ];
  }
  return [
    ...identity,
    { accessorKey: "warehouse", header: "Warehouse" },
    { accessorKey: "expiry", header: "Expiry" },
    { accessorKey: "quantity", header: "On-hand", meta: { align: "right" } },
    {
      accessorKey: "amount",
      header: "Stock value",
      meta: { align: "right" },
      cell: ({ row }) => (
        <span className="numeric font-semibold">
          {formatMoney(row.original.amount ?? 0, currency)}
        </span>
      ),
    },
    {
      id: "alerts",
      header: "Alerts",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.low ? <StatusBadge label="Low" tone="warning" /> : null}
          {row.original.expiring ? <StatusBadge label="Expiring" tone="warning" /> : null}
          {row.original.dead ? <StatusBadge label="Dead stock" tone="neutral" /> : null}
          {!row.original.low && !row.original.expiring && !row.original.dead ? (
            <span className="text-secondary">—</span>
          ) : null}
        </div>
      ),
    },
  ];
}

function ReportPanel({ kind }: { kind: ReportKind }) {
  const canExport = useHasPermission("reports.export");
  const [filters, setFilters] = useState<ReportFilters>({});
  const [page, setPage] = useState(1);
  const [format, setFormat] = useState<"xlsx" | "csv">("xlsx");
  const report = useQuery<ReportData>({
    queryKey: ["report", kind, filters, page],
    queryFn: () => reportQuery(kind, { ...filters, page }),
  });
  const options = useQuery({
    queryKey: ["report-options"],
    queryFn: getReportOptions,
  });
  const exporting = useMutation({
    mutationFn: () => downloadReport(kind, filters, format),
    onSuccess: () => toast.success(`${reportLabels[kind]} report downloaded`),
    onError: () => toast.error("Report could not be downloaded"),
  });

  if (report.isPending)
    return <LoadingState label={`Loading ${reportLabels[kind].toLowerCase()} report…`} />;
  if (report.isError || !report.data)
    return (
      <ErrorState
        title={`${reportLabels[kind]} report could not be loaded`}
        onRetry={() => report.refetch()}
      />
    );
  const data = report.data;
  const currency = data.meta.currency;
  const summary = (() => {
    if (kind === "sales") {
      const value = (data as SalesReport).summary;
      return [
        ["Customers", value.customer_count],
        ["Orders", value.order_count],
        ["Sales", formatMoney(value.sales_amount, currency)],
        ["Collected", formatMoney(value.collected_amount, currency)],
      ];
    }
    if (kind === "products") {
      const value = (data as ProductsReport).summary;
      return [
        ["Quantity sold", value.sale_quantity],
        ["Products", value.product_count],
        ["Item discounts", formatMoney(value.item_discount, currency)],
        ["Sale amount", formatMoney(value.sale_amount, currency)],
      ];
    }
    if (kind === "receivables") {
      const value = (data as ReceivablesReport).summary;
      return [
        ["Customers", value.customer_count],
        ["Orders", value.order_count],
        ["Outstanding", formatMoney(value.total_outstanding, currency)],
        ["90+ days", formatMoney(value.aging["90_plus"], currency)],
      ];
    }
    const value = (data as InventoryReport).summary;
    return [
      ["Stock value", formatMoney(value.stock_value, currency)],
      ["Low stock", value.low_stock_count],
      ["Expiring soon", value.expiring_soon_count],
      ["Dead stock", value.dead_stock_count],
    ];
  })();

  const updateFilter = (name: string, value: string) => {
    setPage(1);
    setFilters((current) => ({ ...current, [name]: value || undefined }));
  };
  const hasDates = kind !== "inventory";
  const hasWarehouse = kind !== "receivables";
  return (
    <div className="space-y-4">
      <FilterBar>
        {hasDates ? (
          <>
            <FilterField label="From" htmlFor={`${kind}-from`}>
              <input
                id={`${kind}-from`}
                type="date"
                className="control-base w-full"
                value={filters.date_from ?? ""}
                onChange={(event) => updateFilter("date_from", event.target.value)}
              />
            </FilterField>
            <FilterField label="To" htmlFor={`${kind}-to`}>
              <input
                id={`${kind}-to`}
                type="date"
                className="control-base w-full"
                value={filters.date_to ?? ""}
                onChange={(event) => updateFilter("date_to", event.target.value)}
              />
            </FilterField>
          </>
        ) : null}
        {hasWarehouse ? (
          <FilterField label="Warehouse" htmlFor={`${kind}-warehouse`}>
            <select
              id={`${kind}-warehouse`}
              className="control-base w-full"
              value={filters.warehouse_id ?? ""}
              onChange={(event) => updateFilter("warehouse_id", event.target.value)}
            >
              <option value="">All warehouses</option>
              {options.data?.warehouses.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </FilterField>
        ) : null}
        {kind === "sales" || kind === "receivables" ? (
          <FilterField label="Customer" htmlFor={`${kind}-customer`}>
            <select
              id={`${kind}-customer`}
              className="control-base w-full"
              value={filters.customer_id ?? ""}
              onChange={(event) => updateFilter("customer_id", event.target.value)}
            >
              <option value="">All customers</option>
              {options.data?.customers.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </FilterField>
        ) : null}
        {kind === "products" || kind === "inventory" ? (
          <>
            <FilterField label="Category" htmlFor={`${kind}-category`}>
              <select
                id={`${kind}-category`}
                className="control-base w-full"
                value={filters.category_id ?? ""}
                onChange={(event) => updateFilter("category_id", event.target.value)}
              >
                <option value="">All categories</option>
                {options.data?.categories.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </FilterField>
            <FilterField label="Brand" htmlFor={`${kind}-brand`}>
              <select
                id={`${kind}-brand`}
                className="control-base w-full"
                value={filters.brand_id ?? ""}
                onChange={(event) => updateFilter("brand_id", event.target.value)}
              >
                <option value="">All brands</option>
                {options.data?.brands.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </FilterField>
          </>
        ) : null}
        <div className="flex items-end gap-2 sm:ml-auto">
          {canExport ? (
            <>
              <label className="sr-only" htmlFor={`${kind}-format`}>
                Export format
              </label>
              <select
                id={`${kind}-format`}
                className="control-base w-24"
                value={format}
                onChange={(event) => setFormat(event.target.value as "xlsx" | "csv")}
              >
                <option value="xlsx">XLSX</option>
                <option value="csv">CSV</option>
              </select>
              <Button
                type="button"
                variant="secondary"
                disabled={exporting.isPending}
                onClick={() => exporting.mutate()}
              >
                <Download aria-hidden="true" />
                {exporting.isPending ? "Preparing…" : "Export"}
              </Button>
            </>
          ) : null}
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setFilters({});
              setPage(1);
            }}
          >
            Reset
          </Button>
        </div>
      </FilterBar>
      <section
        aria-label={`${reportLabels[kind]} report summary`}
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
      >
        {summary.map(([label, value]) => (
          <article key={String(label)} className="surface-card p-4">
            <p className="text-xs font-semibold text-secondary">{label}</p>
            <p className="numeric mt-2 text-xl font-semibold">{value}</p>
          </article>
        ))}
      </section>
      <DataTable
        columns={columns(kind, currency)}
        data={normalizedRows(kind, data)}
        ariaLabel={`${reportLabels[kind]} report`}
        getRowId={(row) => row.id}
        pageSize={data.page_size}
        selectable={false}
        showPagination={false}
      />
      <Pagination
        page={data.page}
        pageCount={Math.ceil(data.total / data.page_size)}
        canPrevious={data.page > 1}
        canNext={data.page * data.page_size < data.total}
        onPrevious={() => setPage((current) => Math.max(1, current - 1))}
        onNext={() => setPage((current) => current + 1)}
      />
      <p className="text-xs text-secondary">
        Generated {new Date(data.meta.generated_at).toLocaleString("en-TZ")} ·{" "}
        {data.meta.company_name}
      </p>
    </div>
  );
}

export function ReportsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Business intelligence"
        title="Reports"
        subtitle="Warehouse-aware sales, product, receivables, and inventory reporting with company-letterhead exports."
        actions={
          <span className="inline-flex items-center gap-2 rounded-pill bg-primary-50 px-3 py-2 text-xs font-semibold text-primary-800">
            <FileSpreadsheet aria-hidden="true" className="size-4" />
            Live operational data
          </span>
        }
      />
      <Tabs
        ariaLabel="Report types"
        items={(Object.keys(reportLabels) as ReportKind[]).map((kind) => ({
          value: kind,
          label: reportLabels[kind],
          content: <ReportPanel kind={kind} />,
        }))}
      />
    </div>
  );
}
