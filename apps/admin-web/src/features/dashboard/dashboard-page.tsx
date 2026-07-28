import { motion, useReducedMotion } from "motion/react";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Boxes,
  CalendarClock,
  ClipboardList,
  Download,
  PackageCheck,
  Plus,
  Store,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { EntityDrawer } from "@/components/ui/entity-drawer";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { useHasPermission } from "@/features/auth/auth-store";
import { previewOrders } from "@/features/orders/orders.data";
import { copy } from "@/lib/copy";
import { cn, formatCompact, formatMoney } from "@/lib/utils";

type Kpi = {
  label: string;
  value: string;
  helper: string;
  change: string;
  direction: "up" | "down";
  icon: LucideIcon;
  warning?: boolean;
};

const kpis: Kpi[] = [
  {
    label: "Orders today",
    value: "24",
    helper: "6 awaiting review",
    change: "+12%",
    direction: "up",
    icon: ClipboardList,
  },
  {
    label: "Today’s sales",
    value: formatMoney(18460000, "TZS"),
    helper: "Collected and pending",
    change: "+8.4%",
    direction: "up",
    icon: TrendingUp,
  },
  {
    label: "Active products",
    value: formatCompact(1284),
    helper: "42 awaiting verification",
    change: "+18",
    direction: "up",
    icon: PackageCheck,
  },
  {
    label: "Verified customers",
    value: "368",
    helper: "11 under review",
    change: "+6",
    direction: "up",
    icon: Store,
  },
  {
    label: "Low-stock SKUs",
    value: "17",
    helper: "5 need action today",
    change: "+3",
    direction: "down",
    icon: Boxes,
    warning: true,
  },
  {
    label: "Expiring soon",
    value: "9",
    helper: "Within the next 90 days",
    change: "-2",
    direction: "up",
    icon: CalendarClock,
    warning: true,
  },
];

const stockAlerts = [
  {
    name: "Amoxicillin 500mg Capsules",
    detail: "Batch AMX-1407 · 32 available",
    status: "Low stock",
    tone: "warning" as const,
  },
  {
    name: "Metformin 500mg Tablets",
    detail: "Batch MTF-2231 · expires 18 Aug",
    status: "Expiring soon",
    tone: "warning" as const,
  },
  {
    name: "ORS Sachets 20.5g",
    detail: "Batch ORS-0918 · 0 available",
    status: "Out of stock",
    tone: "danger" as const,
  },
  {
    name: "Paracetamol 500mg Tablets",
    detail: "Batch PCM-8120 · 46 available",
    status: "Low stock",
    tone: "warning" as const,
  },
];

const salesPoints = [28, 42, 37, 56, 51, 72, 66, 86, 79, 98, 92, 112];

export function DashboardPage() {
  const prefersReducedMotion = useReducedMotion();
  const canExportReports = useHasPermission("reports.export");
  const canCreateOrders = useHasPermission("orders.create");
  const canViewInventory = useHasPermission("inventory.view");
  const canViewOrders = useHasPermission("orders.view");

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={copy.dashboard.eyebrow}
        title={copy.dashboard.title}
        subtitle={copy.dashboard.subtitle}
        actions={
          canExportReports || canCreateOrders ? (
            <>
              {canExportReports ? (
                <Button variant="secondary">
                  <Download aria-hidden="true" />
                  {copy.dashboard.actions.report}
                </Button>
              ) : null}
              {canCreateOrders ? (
                <EntityDrawer
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

      <section
        aria-label="Key performance indicators"
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6"
      >
        {kpis.map((item, index) => {
          const Icon = item.icon;
          const ChangeIcon = item.direction === "up" ? ArrowUpRight : ArrowDownRight;
          return (
            <motion.article
              key={item.label}
              initial={
                prefersReducedMotion ? false : { opacity: 0, transform: "translateY(12px)" }
              }
              animate={{ opacity: 1, transform: "translateY(0)" }}
              transition={{
                duration: 0.22,
                delay: prefersReducedMotion ? 0 : Math.min(index * 0.025, 0.125),
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
                    "numeric inline-flex items-center text-[11px] font-semibold text-success",
                    item.direction === "down" && "text-warning",
                  )}
                >
                  <ChangeIcon aria-hidden="true" className="size-3" />
                  {item.change}
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
        <section
          className="surface-card overflow-hidden"
          aria-labelledby="sales-pulse-title"
        >
          <div className="flex flex-col gap-3 border-b border-border px-5 py-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2
                id="sales-pulse-title"
                className="font-display text-xl font-semibold tracking-tight text-foreground"
              >
                {copy.dashboard.salesTitle}
              </h2>
              <p className="mt-1 text-xs text-secondary">{copy.dashboard.salesSubtitle}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-primary-500" />
              <span className="text-xs font-semibold text-secondary">
                Gross sales · TZS
              </span>
            </div>
          </div>
          <div className="p-5">
            <div className="mb-5 flex items-end justify-between">
              <div>
                <p className="text-xs font-semibold text-secondary">This week</p>
                <p className="numeric mt-1 text-2xl font-semibold tracking-tight">
                  {formatMoney(67480000, "TZS")}
                </p>
              </div>
              <StatusBadge label="8.4% vs last week" tone="success" />
            </div>
            <div className="relative h-[210px] overflow-hidden rounded-[12px] border border-border bg-[linear-gradient(180deg,#F4FAFC_0%,#FFFFFF_80%)]">
              <div className="absolute inset-x-0 top-1/4 border-t border-dashed border-primary-200/70" />
              <div className="absolute inset-x-0 top-2/4 border-t border-dashed border-primary-200/70" />
              <div className="absolute inset-x-0 top-3/4 border-t border-dashed border-primary-200/70" />
              <svg
                viewBox="0 0 660 210"
                preserveAspectRatio="none"
                className="absolute inset-0 h-full w-full"
                role="img"
                aria-labelledby="weekly-sales-title weekly-sales-description"
              >
                <title id="weekly-sales-title">Illustrative weekly sales trend</title>
                <desc id="weekly-sales-description">
                  Sales generally rise over the displayed twelve periods.
                </desc>
                <defs>
                  <linearGradient id="sales-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#50A0C0" stopOpacity="0.24" />
                    <stop offset="100%" stopColor="#50A0C0" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path
                  d={`M 0 190 ${salesPoints
                    .map((point, index) => {
                      const x = (index / (salesPoints.length - 1)) * 660;
                      const y = 180 - (point / 120) * 150;
                      return `L ${x} ${y}`;
                    })
                    .join(" ")} L 660 210 L 0 210 Z`}
                  fill="url(#sales-fill)"
                />
                <path
                  d={salesPoints
                    .map((point, index) => {
                      const x = (index / (salesPoints.length - 1)) * 660;
                      const y = 180 - (point / 120) * 150;
                      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
                    })
                    .join(" ")}
                  fill="none"
                  stroke="#4187A6"
                  strokeWidth="3"
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                />
              </svg>
              <div className="absolute inset-x-4 bottom-3 flex justify-between text-[10px] font-medium text-muted">
                <span>Mon</span>
                <span>Tue</span>
                <span>Wed</span>
                <span>Thu</span>
                <span>Fri</span>
                <span>Sat</span>
                <span>Sun</span>
              </div>
            </div>
          </div>
        </section>

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
                    className="font-display text-xl font-semibold tracking-tight text-foreground"
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
              {stockAlerts.map((item) => (
                <button
                  key={item.name}
                  type="button"
                  className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors duration-micro hover:bg-[var(--row-hover)]"
                >
                  <span className="size-2 shrink-0 rounded-full bg-warning" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-foreground">
                      {item.name}
                    </span>
                    <span className="numeric mt-0.5 block truncate text-[11px] text-secondary">
                      {item.detail}
                    </span>
                  </span>
                  <StatusBadge label={item.status} tone={item.tone} />
                </button>
              ))}
            </div>
            <div className="border-t border-border bg-[#FBFCFB] px-5 py-3">
              <Button variant="ghost" size="sm" className="-ml-3">
                View inventory
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
                className="font-display text-xl font-semibold tracking-tight text-foreground"
              >
                {copy.dashboard.recentTitle}
              </h2>
              <p className="mt-1 text-xs text-secondary">{copy.dashboard.recentSubtitle}</p>
            </div>
            <Button asChild variant="secondary" size="sm">
              <a href="/orders">View all orders</a>
            </Button>
          </div>
          <div className="scrollbar-subtle overflow-x-auto">
            <table className="w-full min-w-[720px]" aria-label="Recent order preview">
              <thead className="bg-[#FBFCFB]">
                <tr className="border-b border-border">
                  {["Order", "Customer", "Location", "Total", "Status"].map((label) => (
                    <th
                      key={label}
                      className="h-11 px-5 text-left text-[10px] font-bold uppercase tracking-[0.09em] text-secondary"
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewOrders.slice(0, 4).map((order) => (
                  <tr
                    key={order.id}
                    className="border-b border-border transition-colors duration-micro last:border-0 hover:bg-[var(--row-hover)]"
                  >
                    <td className="h-14 px-5 font-mono text-xs font-semibold text-primary-700">
                      {order.orderNumber}
                    </td>
                    <td className="px-5 text-sm font-semibold">{order.customer}</td>
                    <td className="px-5 text-sm text-secondary">{order.location}</td>
                    <td className="numeric px-5 text-sm font-semibold">
                      {formatMoney(order.total, "TZS")}
                    </td>
                    <td className="px-5">
                      <StatusBadge
                        label={order.status.replaceAll("_", " ").toLowerCase()}
                        tone={
                          order.status === "DELIVERED"
                            ? "success"
                            : order.status === "FAILED"
                              ? "danger"
                              : "warning"
                        }
                        className="capitalize"
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
