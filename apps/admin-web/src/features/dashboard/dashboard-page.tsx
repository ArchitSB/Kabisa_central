import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ChevronRight,
  ShieldCheck,
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
  const canViewCustomers = useHasPermission("customers.view");
  const canViewProducts = useHasPermission("products.view");
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
  const pulse = useMemo(
    () =>
      (data?.sales_pulse ?? []).map((point) => ({
        ...point,
        gross_sales: Number(point.gross_sales),
        label: new Intl.DateTimeFormat("en-TZ", { weekday: "short" }).format(
          new Date(`${point.date}T12:00:00`),
        ),
      })),
    [data?.sales_pulse],
  );
  const pulseTotal = useMemo(
    () =>
      (data?.sales_pulse ?? []).reduce((sum, point) => sum + Number(point.gross_sales), 0),
    [data?.sales_pulse],
  );

  if (dashboard.isPending) return <LoadingState label="Loading live operations…" />;
  if (dashboard.isError || !data) {
    return (
      <ErrorState
        title="The operations overview could not be loaded"
        onRetry={() => dashboard.refetch()}
      />
    );
  }

  const attention =
    (data.orders_awaiting_review ?? 0) +
    (data.customers_under_review ?? 0) +
    (data.products_awaiting_verification ?? 0);
  return (
    <div className="ops-overview">
      <header className="ops-overview-header">
        <div>
          <div className="ops-eyebrow">
            <CalendarClock size={13} />
            {new Intl.DateTimeFormat("en-TZ", {
              dateStyle: "full",
              timeZone: "Africa/Dar_es_Salaam",
            }).format(new Date())}
          </div>
          <h1>Your operations, in focus.</h1>
          <p>A clear view of the work that keeps better care moving.</p>
        </div>
        <div className="ops-overview-actions">
          {canExportReports && (
            <Button
              variant="secondary"
              disabled={exportReport.isPending}
              onClick={() => exportReport.mutate()}
            >
              <Download />
              {exportReport.isPending ? "Preparing…" : "Export report"}
            </Button>
          )}
          {canCreateOrders && (
            <CreateOrderDrawer
              trigger={
                <Button>
                  <Plus />
                  Create order
                </Button>
              }
            />
          )}
        </div>
      </header>
      <div className="ops-context-strip">
        <span>
          <strong>Business overview</strong> <span aria-hidden="true"> / </span> Current
          operational data
        </span>
        {canViewInventory && (
          <label>
            Stock location
            <select
              className="control-base"
              value={warehouseId}
              onChange={(e) => setWarehouseId(e.target.value)}
            >
              <option value="">All warehouses</option>
              {warehouses.data?.items.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <section aria-label="Key performance indicators" className="ops-metric-grid">
        {kpis
          .filter((k) => !k.warning)
          .map((item, index) => {
            const delta = item.metric.delta_percent;
            const DeltaIcon =
              delta === null ? Minus : delta >= 0 ? ArrowUpRight : ArrowDownRight;
            return (
              <motion.article
                key={item.label}
                className="ops-metric"
                initial={prefersReducedMotion ? false : { opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: prefersReducedMotion ? 0 : 0.3,
                  delay: prefersReducedMotion ? 0 : index * 0.045,
                  ease: [0.2, 0, 0, 1],
                }}
              >
                <div className="ops-metric-heading">
                  <span>{item.label}</span>
                  <span className="ops-metric-icon">
                    <item.icon size={16} />
                  </span>
                </div>
                <p className="ops-metric-value">{item.value}</p>
                <div className="ops-metric-footer">
                  <span
                    className={cn(
                      "ops-metric-delta",
                      delta !== null && delta < 0 && "text-secondary",
                    )}
                  >
                    <DeltaIcon size={12} />
                    {delta === null ? "—" : `${delta > 0 ? "+" : ""}${delta}%`}
                  </span>
                  <span>{item.metric.comparison}</span>
                </div>
                <p className="ops-metric-helper">{item.helper}</p>
              </motion.article>
            );
          })}
      </section>
      <div className="ops-overview-main">
        {canViewOrders && (
          <section className="ops-panel" aria-labelledby="sales-pulse-title">
            <div className="ops-panel-heading">
              <div>
                <h2 id="sales-pulse-title">Sales performance</h2>
                <p>Committed orders over the last seven days</p>
              </div>
              <span className="rounded-md border border-border px-2 py-1 text-[10px] text-secondary">
                Last 7 days
              </span>
            </div>
            <div className="ops-chart-summary">
              <strong>{formatMoney(pulseTotal, data.currency)}</strong>
              <span>
                <i />
                Gross sales
              </span>
            </div>
            <div className="ops-chart">
              <ChartContainer>
                <AreaChart data={pulse} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="sales-fill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#193c69" stopOpacity={0.16} />
                      <stop offset="100%" stopColor="#193c69" stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke="#e8edf4" strokeDasharray="3 5" />
                  <XAxis
                    dataKey="label"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#65758b", fontSize: 10 }}
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
                    stroke="#193c69"
                    strokeWidth={2.5}
                    fill="url(#sales-fill)"
                    isAnimationActive={!prefersReducedMotion}
                    animationDuration={450}
                  />
                </AreaChart>
              </ChartContainer>
            </div>
            <div className="ops-chart-caption">
              <ShieldCheck size={13} />
              Figures reflect recorded orders; cancelled orders are excluded.
            </div>
          </section>
        )}
        <section className="ops-attention" aria-labelledby="attention-title">
          <div className="ops-attention-eyebrow">
            <span className="size-1.5 rounded-full bg-[#ff8a92]" />
            Your next actions
          </div>
          <h2 id="attention-title">Keep things moving.</h2>
          <p>
            {attention
              ? `${attention} items across your review queues.`
              : "Your review queues are up to date."}{" "}
            Pick up where your team needs you.
          </p>
          <div className="ops-action-list">
            {canViewOrders && (
              <Link className="ops-action-link" to="/orders">
                <ClipboardList />
                <span>
                  Review orders<small>Confirm and prepare for fulfilment</small>
                </span>
                <strong>{data.orders_awaiting_review ?? 0}</strong>
                <ChevronRight />
              </Link>
            )}
            {canViewCustomers && (
              <Link className="ops-action-link" to="/customers">
                <Store />
                <span>
                  Verify businesses<small>Review customer applications</small>
                </span>
                <strong>{data.customers_under_review ?? 0}</strong>
                <ChevronRight />
              </Link>
            )}
            {canViewProducts && (
              <Link className="ops-action-link" to="/products">
                <PackageCheck />
                <span>
                  Approve products<small>Check catalog readiness</small>
                </span>
                <strong>{data.products_awaiting_verification ?? 0}</strong>
                <ChevronRight />
              </Link>
            )}
          </div>
        </section>
      </div>
      <section className="ops-risk-strip" aria-label="Inventory and balance overview">
        {kpis
          .filter((k) => k.warning)
          .map((item) => (
            <div className="ops-risk-item" key={item.label}>
              <item.icon />
              <span>
                <strong>{item.value}</strong>
                <small>{item.label}</small>
              </span>
            </div>
          ))}
      </section>
      <div className="ops-bottom-grid">
        {canViewOrders && (
          <section className="ops-panel" aria-labelledby="recent-orders-title">
            <div className="ops-panel-heading">
              <div>
                <h2 id="recent-orders-title">Latest orders</h2>
                <p>The latest activity from your customers</p>
              </div>
              <Link to="/orders">
                All orders <ArrowUpRight size={14} />
              </Link>
            </div>
            <div className="overflow-x-auto scrollbar-subtle">
              <table className="ops-recent-table" aria-label="Recent orders">
                <thead>
                  <tr>
                    {["Order / customer", "Total", "Payment", "Status"].map((label) => (
                      <th key={label}>{label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.recent_orders.map((order) => (
                    <tr key={order.id}>
                      <td>
                        <Link to={`/orders/${order.id}`}>{order.order_number}</Link>
                        <small>{order.customer_name}</small>
                      </td>
                      <td className="numeric whitespace-nowrap">
                        {formatMoney(order.total_amount, data.currency)}
                      </td>
                      <td>
                        <StatusBadge
                          label={paymentStatusLabels[order.payment_status]}
                          tone={order.payment_status === "PAID" ? "success" : "warning"}
                        />
                      </td>
                      <td>
                        <StatusBadge
                          label={orderStatusLabels[order.status]}
                          tone={orderTone(order.status)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!data.recent_orders.length && (
                <p className="ops-empty">New orders will appear here as they arrive.</p>
              )}
            </div>
          </section>
        )}
        {canViewInventory && (
          <section className="ops-panel" aria-labelledby="watchlist-title">
            <div className="ops-panel-heading">
              <div>
                <h2 id="watchlist-title">Stock attention</h2>
                <p>Low stock and approaching expiry</p>
              </div>
              <Link to="/inventory" aria-label="View inventory">
                <ArrowUpRight size={16} />
              </Link>
            </div>
            {data.inventory_watchlist.length ? (
              data.inventory_watchlist.slice(0, 5).map((item) => (
                <button
                  key={`${item.product_id}-${item.warehouse_id}-${item.batch_number}`}
                  className="ops-stock-row"
                  onClick={() =>
                    navigate(
                      canViewProducts ? `/products/${item.product_id}` : "/inventory",
                    )
                  }
                >
                  <span className="ops-stock-symbol">
                    <Boxes size={16} />
                  </span>
                  <span>
                    <strong>{item.product_name}</strong>
                    <small>
                      {item.alert_type === "EXPIRING_SOON" ? "Expiring soon" : "Low stock"}{" "}
                      · {item.on_hand} on hand · {item.warehouse_name}
                    </small>
                  </span>
                  <AlertTriangle size={14} />
                </button>
              ))
            ) : (
              <p className="ops-empty">No inventory alerts need attention.</p>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
