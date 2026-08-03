import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Boxes,
  CalendarClock,
  ClipboardList,
  Download,
  Minus,
  PackageCheck,
  Plus,
  ReceiptText,
  Store,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { useHasPermission } from "@/features/auth/auth-store";
import { listWarehouses } from "@/features/catalog/catalog-api";
import { CreateOrderDrawer } from "@/features/orders/create-order-drawer";
import {
  orderStatusLabels,
  paymentStatusLabels,
  type OrderStatus,
} from "@/features/orders/orders.data";
import { downloadReport, getDashboardSummary } from "@/features/reporting/reporting-api";
import type { DashboardMetric } from "@/features/reporting/types";
import { copy } from "@/lib/copy";
import { cn, formatCompact, formatMoney } from "@/lib/utils";

type Kpi = {
  label: string;
  value: string;
  helper: string;
  metric: DashboardMetric;
  icon: LucideIcon;
  warning?: boolean;
};

function orderTone(status: OrderStatus) {
  if (status === "DELIVERED") return "success" as const;
  if (["FAILED", "UNFOUND", "CANCELLED"].includes(status)) return "danger" as const;
  return "warning" as const;
}

export function DashboardPage() {
  const [warehouseId, setWarehouseId] = useState("");
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();
  const canExportReports = useHasPermission("reports.export");
  const canCreateOrders = useHasPermission("orders.create");
  const canViewInventory = useHasPermission("inventory.view");
  const canViewOrders = useHasPermission("orders.view");
  const dashboard = useQuery({
    queryKey: ["dashboard-summary", warehouseId],
    queryFn: () => getDashboardSummary(warehouseId || undefined),
  });
  const warehouses = useQuery({
    queryKey: ["warehouses", "dashboard-options"],
    queryFn: () => listWarehouses(),
    enabled: canViewInventory,
  });
  const exportReport = useMutation({
    mutationFn: () => downloadReport("sales", {}, "xlsx"),
    onSuccess: () => toast.success("Sales report downloaded"),
    onError: () => toast.error("Report could not be downloaded"),
  });
  const data = dashboard.data;
  const kpis = useMemo<Kpi[]>(() => {
    if (!data) return [];
    return [
      data.orders_today && {
        label: "Orders today",
        value: formatCompact(data.orders_today.value),
        helper: `${data.orders_awaiting_review ?? 0} awaiting review`,
        metric: data.orders_today,
        icon: ClipboardList,
      },
      data.sales_today && {
        label: "Today’s sales",
        value: formatMoney(data.sales_today.value, data.currency),
        helper: `${formatMoney(data.sales_collected_today ?? 0, data.currency)} collected`,
        metric: data.sales_today,
        icon: TrendingUp,
      },
      data.active_products && {
        label: "Active products",
        value: formatCompact(data.active_products.value),
        helper: `${data.products_awaiting_verification ?? 0} awaiting verification`,
        metric: data.active_products,
        icon: PackageCheck,
      },
      data.verified_customers && {
        label: "Verified customers",
        value: formatCompact(data.verified_customers.value),
        helper: `${data.customers_under_review ?? 0} under review`,
        metric: data.verified_customers,
        icon: Store,
      },
      data.low_stock_skus && {
        label: "Low-stock SKUs",
        value: formatCompact(data.low_stock_skus.value),
        helper: `${data.low_stock_needing_action ?? 0} need action`,
        metric: data.low_stock_skus,
        icon: Boxes,
        warning: true,
      },
      data.expiring_soon && {
        label: "Expiring soon",
        value: formatCompact(data.expiring_soon.value),
        helper: data.expiring_soon.comparison,
        metric: data.expiring_soon,
        icon: CalendarClock,
        warning: true,
      },
      data.outstanding_receivables && {
        label: "Receivables",
        value: formatMoney(data.outstanding_receivables.value, data.currency),
        helper: "Committed order balances",
        metric: data.outstanding_receivables,
        icon: ReceiptText,
        warning: true,
      },
    ].filter(Boolean) as Kpi[];
  }, [data]);

  if (dashboard.isPending) return <LoadingState label="Loading live operations…" />;
  if (dashboard.isError || !data) {
    return (
      <ErrorState
        title="The operations overview could not be loaded"
        onRetry={() => dashboard.refetch()}
      />
    );
  }

  const pulseTotal = data.sales_pulse.reduce((sum, point) => sum + point.gross_sales, 0);
  const pulse = data.sales_pulse.map((point) => ({
    ...point,
    label: new Intl.DateTimeFormat("en-TZ", { weekday: "short" }).format(
      new Date(`${point.date}T12:00:00`),
    ),
  }));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={new Intl.DateTimeFormat("en-TZ", { dateStyle: "full" }).format(new Date())}
        title={copy.dashboard.title}
        subtitle={copy.dashboard.subtitle}
        actions={
          canExportReports || canCreateOrders ? (
            <>
              {canExportReports ? (
                <Button
                  variant="secondary"
                  disabled={exportReport.isPending}
                  onClick={() => exportReport.mutate()}
                >
                  <Download aria-hidden="true" />
                  {exportReport.isPending ? "Preparing…" : copy.dashboard.actions.report}
                </Button>
              ) : null}
              {canCreateOrders ? (
                <CreateOrderDrawer
                  trigger={
                    <Button>
                      <Plus aria-hidden="true" />
                      {copy.dashboard.actions.order}
                    </Button>
                  }
                />
              ) : null}
            </>
          ) : null
        }
      />

      {canViewInventory ? (
        <div className="flex justify-end">
          <label className="flex items-center gap-2 text-xs font-semibold text-secondary">
            Warehouse
            <select
              className="control-base min-w-52"
              value={warehouseId}
              onChange={(event) => setWarehouseId(event.target.value)}
            >
              <option value="">All warehouses</option>
              {warehouses.data?.items.map((warehouse) => (
                <option key={warehouse.id} value={warehouse.id}>
                  {warehouse.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : null}

      <section
        aria-label="Key performance indicators"
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7"
      >
        {kpis.map((item, index) => {
          const Icon = item.icon;
          const delta = item.metric.delta_percent;
          const DeltaIcon =
            delta === null ? Minus : delta >= 0 ? ArrowUpRight : ArrowDownRight;
          return (
            <motion.article
              key={item.label}
              initial={
                prefersReducedMotion ? false : { opacity: 0, transform: "translateY(12px)" }
              }
              animate={{ opacity: 1, transform: "translateY(0)" }}
              transition={{
                duration: 0.22,
                delay: prefersReducedMotion ? 0 : Math.min(index * 0.025, 0.15),
                ease: [0.2, 0, 0, 1],
              }}
              className="surface-card min-w-0 p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <span
                  className={cn(
                    "flex size-9 shrink-0 items-center justify-center rounded-control bg-primary-50 text-primary-700",
                    item.warning && "bg-warning-surface text-warning",
                  )}
                >
                  <Icon aria-hidden="true" className="size-[18px]" />
                </span>
                <span
                  className={cn(
                    "numeric inline-flex items-center text-[11px] font-semibold",
                    delta === null
                      ? "text-muted"
                      : item.warning && delta > 0
                        ? "text-warning"
                        : delta >= 0
                          ? "text-success"
                          : "text-secondary",
                  )}
                  title={item.metric.comparison}
                >
                  <DeltaIcon aria-hidden="true" className="size-3" />
                  {delta === null ? "New" : `${delta > 0 ? "+" : ""}${delta}%`}
                </span>
              </div>
              <p className="mt-5 text-xs font-semibold text-secondary">{item.label}</p>
              <p className="numeric mt-1 truncate text-[21px] font-semibold tracking-[-0.02em] text-foreground">
                {item.value}
              </p>
              <p className="mt-1 truncate text-[11px] text-muted">{item.helper}</p>
            </motion.article>
          );
        })}
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,.75fr)]">
        {canViewOrders ? (
          <section
            className="surface-card overflow-hidden"
            aria-labelledby="sales-pulse-title"
          >
            <div className="flex flex-col gap-3 border-b border-border px-5 py-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2
                  id="sales-pulse-title"
                  className="font-display text-xl font-semibold tracking-tight"
                >
                  {copy.dashboard.salesTitle}
                </h2>
                <p className="mt-1 text-xs text-secondary">
                  {copy.dashboard.salesSubtitle}
                </p>
              </div>
              <span className="inline-flex items-center gap-2 text-xs font-semibold text-secondary">
                <span className="size-2 rounded-full bg-primary-500" /> Gross sales ·{" "}
                {data.currency}
              </span>
            </div>
            <div className="p-5">
              <div className="mb-5 flex items-end justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold text-secondary">Last 7 days</p>
                  <p className="numeric mt-1 text-2xl font-semibold tracking-tight">
                    {formatMoney(pulseTotal, data.currency)}
                  </p>
                </div>
                <StatusBadge label="Committed sales" tone="success" />
              </div>
              <ChartContainer>
                <AreaChart data={pulse} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="sales-fill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#50A0C0" stopOpacity={0.24} />
                      <stop offset="100%" stopColor="#50A0C0" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke="#E8EAE9" strokeDasharray="4 4" />
                  <XAxis
                    dataKey="label"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#68747E", fontSize: 11 }}
                  />
                  <YAxis hide />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) => formatMoney(value, data.currency)}
                      />
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="gross_sales"
                    stroke="#4187A6"
                    strokeWidth={3}
                    fill="url(#sales-fill)"
                    isAnimationActive={!prefersReducedMotion}
                    animationDuration={220}
                  />
                </AreaChart>
              </ChartContainer>
            </div>
          </section>
        ) : null}

        {canViewInventory ? (
          <section
            className="surface-card overflow-hidden"
            aria-labelledby="watchlist-title"
          >
            <div className="border-b border-border px-5 py-5">
              <div className="flex items-center gap-3">
                <span className="flex size-9 items-center justify-center rounded-control bg-warning-surface text-warning">
                  <AlertTriangle aria-hidden="true" className="size-[18px]" />
                </span>
                <div>
                  <h2
                    id="watchlist-title"
                    className="font-display text-xl font-semibold tracking-tight"
                  >
                    {copy.dashboard.watchlistTitle}
                  </h2>
                  <p className="mt-0.5 text-xs text-secondary">
                    {copy.dashboard.watchlistSubtitle}
                  </p>
                </div>
              </div>
            </div>
            <div className="divide-y divide-border">
              {data.inventory_watchlist.length ? (
                data.inventory_watchlist.map((item) => (
                  <button
                    key={`${item.product_id}-${item.batch_number}`}
                    type="button"
                    className="flex w-full cursor-pointer items-center gap-3 px-5 py-4 text-left transition-colors duration-micro hover:bg-[var(--row-hover)]"
                    onClick={() => navigate(`/products/${item.product_id}`)}
                  >
                    <span className="size-2 shrink-0 rounded-full bg-warning" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold">
                        {item.product_name}
                      </span>
                      <span className="numeric mt-0.5 block truncate text-[11px] text-secondary">
                        {item.warehouse_name} · {item.batch_number} · {item.on_hand} on-hand
                      </span>
                    </span>
                    <StatusBadge
                      label={
                        item.alert_type === "EXPIRING_SOON" ? "Expiring soon" : "Low stock"
                      }
                      tone="warning"
                    />
                  </button>
                ))
              ) : (
                <p className="px-5 py-10 text-center text-sm text-secondary">
                  No inventory alerts need attention.
                </p>
              )}
            </div>
            <div className="border-t border-border bg-[#FBFCFB] px-5 py-3">
              <Button asChild variant="ghost" size="sm" className="-ml-3">
                <Link to="/inventory">View inventory</Link>
              </Button>
            </div>
          </section>
        ) : null}
      </div>

      {canViewOrders ? (
        <section
          className="surface-card overflow-hidden"
          aria-labelledby="recent-orders-title"
        >
          <div className="flex flex-col gap-3 border-b border-border px-5 py-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2
                id="recent-orders-title"
                className="font-display text-xl font-semibold tracking-tight"
              >
                {copy.dashboard.recentTitle}
              </h2>
              <p className="mt-1 text-xs text-secondary">{copy.dashboard.recentSubtitle}</p>
            </div>
            <Button asChild variant="secondary" size="sm">
              <Link to="/orders">View all orders</Link>
            </Button>
          </div>
          <div className="scrollbar-subtle overflow-x-auto">
            <table className="w-full min-w-[780px]" aria-label="Recent orders">
              <thead className="bg-[#FBFCFB]">
                <tr className="border-b border-border">
                  {["Order", "Customer", "Location", "Payment", "Total", "Status"].map(
                    (label) => (
                      <th
                        key={label}
                        className="h-11 px-5 text-left text-[10px] font-bold uppercase tracking-[0.09em] text-secondary"
                      >
                        {label}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {data.recent_orders.map((order) => (
                  <tr
                    key={order.id}
                    className="border-b border-border transition-colors duration-micro last:border-0 hover:bg-[var(--row-hover)]"
                  >
                    <td className="h-14 px-5">
                      <Link
                        className="font-mono text-xs font-semibold text-primary-700 hover:text-primary-800"
                        to={`/orders/${order.id}`}
                      >
                        {order.order_number}
                      </Link>
                    </td>
                    <td className="px-5 text-sm font-semibold">{order.customer_name}</td>
                    <td className="px-5 text-sm text-secondary">
                      {order.delivery_location ?? "—"}
                    </td>
                    <td className="px-5">
                      <StatusBadge
                        label={paymentStatusLabels[order.payment_status]}
                        tone={order.payment_status === "PAID" ? "success" : "warning"}
                      />
                    </td>
                    <td className="numeric px-5 text-sm font-semibold">
                      {formatMoney(order.total_amount, data.currency)}
                    </td>
                    <td className="px-5">
                      <StatusBadge
                        label={orderStatusLabels[order.status]}
                        tone={orderTone(order.status)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </div>
  );
}
