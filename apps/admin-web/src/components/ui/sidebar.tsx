import {
  BadgePercent,
  Boxes,
  ChartNoAxesCombined,
  ChevronRight,
  CircleUserRound,
  ClipboardList,
  ContactRound,
  LayoutDashboard,
  LogOut,
  PackageSearch,
  Settings,
  ShieldCheck,
  Store,
  Tags,
  Truck,
  X,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { copy } from "@/lib/copy";
import { cn } from "@/lib/utils";

type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

const navigation: Array<{ label: string; items: NavItem[] }> = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", href: "/", icon: LayoutDashboard }],
  },
  {
    label: "Operations",
    items: [
      { label: "Orders", href: "/orders", icon: ClipboardList },
      { label: "Products", href: "/products", icon: PackageSearch },
      { label: "Inventory", href: "/inventory", icon: Boxes },
      { label: "Customers", href: "/customers", icon: Store },
      { label: "Delivery agents", href: "/delivery-agents", icon: Truck },
    ],
  },
  {
    label: "Management",
    items: [
      { label: "Categories", href: "/categories", icon: Tags },
      { label: "Brands", href: "/brands", icon: ContactRound },
      { label: "Coupons", href: "/coupons", icon: BadgePercent },
      { label: "Reports", href: "/reports", icon: ChartNoAxesCombined },
      { label: "Roles", href: "/roles", icon: ShieldCheck },
      { label: "Settings", href: "/settings", icon: Settings },
    ],
  },
];

type SidebarProps = {
  mobile?: boolean;
  onClose?: () => void;
};

export function Sidebar({ mobile = false, onClose }: SidebarProps) {
  return (
    <aside
      className={cn(
        "flex h-dvh w-[260px] flex-col overflow-hidden bg-sidebar text-sidebar-foreground",
        mobile ? "w-[min(86vw,320px)]" : "fixed inset-y-0 left-0 z-30",
      )}
      aria-label="Primary navigation"
    >
      <div className="h-1 w-full bg-sidebar-accent" />
      <div className="flex h-[82px] shrink-0 items-center justify-between border-b border-white/[0.07] px-6">
        <NavLink to="/" className="group flex items-center gap-3" onClick={onClose}>
          <span className="flex size-9 items-center justify-center rounded-[11px] border border-primary-400/35 bg-primary-500/10 font-display text-lg font-semibold text-primary-400 transition-colors duration-standard group-hover:bg-primary-500/20">
            K
          </span>
          <span>
            <span className="block font-display text-xl font-semibold tracking-[-0.02em] text-white">
              {copy.brand.name}
            </span>
            <span className="block text-[10px] font-bold uppercase tracking-[0.18em] text-sidebar-muted">
              {copy.brand.product}
            </span>
          </span>
        </NavLink>
        {mobile ? (
          <button
            type="button"
            aria-label="Close navigation"
            className="flex size-10 items-center justify-center rounded-control text-sidebar-muted transition-colors hover:bg-white/[0.08] hover:text-white"
            onClick={onClose}
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        ) : null}
      </div>

      <nav className="scrollbar-subtle flex-1 overflow-y-auto px-3 py-5">
        <p className="px-3 pb-4 text-[10px] font-bold uppercase tracking-[0.18em] text-sidebar-muted">
          {copy.brand.section}
        </p>
        <div className="space-y-5">
          {navigation.map((section) => (
            <div key={section.label}>
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-sidebar-muted/75">
                {section.label}
              </p>
              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.href}
                      to={item.href}
                      end={item.href === "/"}
                      onClick={onClose}
                      className={({ isActive }) =>
                        cn(
                          "group flex min-h-10 items-center gap-3 rounded-[10px] px-3 text-[13px] font-medium text-sidebar-muted transition-colors duration-standard ease-kabisa hover:bg-white/[0.06] hover:text-sidebar-foreground",
                          isActive &&
                            "bg-sidebar-active font-semibold text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,.05)] hover:bg-sidebar-active hover:text-white",
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <Icon
                            aria-hidden={true}
                            className={cn(
                              "size-[18px] shrink-0 transition-colors duration-standard",
                              isActive
                                ? "text-white"
                                : "text-sidebar-muted group-hover:text-primary-400",
                            )}
                          />
                          <span className="min-w-0 flex-1 truncate">{item.label}</span>
                          {isActive ? (
                            <ChevronRight
                              aria-hidden="true"
                              className="size-3.5 text-white/75"
                            />
                          ) : null}
                        </>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </nav>

      <div className="shrink-0 border-t border-white/[0.07] p-3">
        <div className="flex items-center gap-3 rounded-[12px] bg-white/[0.035] p-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary-500/15 text-primary-400">
            <CircleUserRound aria-hidden="true" className="size-5" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold text-sidebar-foreground">
              Neema Mushi
            </span>
            <span className="block truncate text-[11px] text-sidebar-muted">
              Super admin
            </span>
          </span>
          <button
            type="button"
            aria-label="Log out"
            title="Authentication begins in Phase 1"
            className="flex size-9 shrink-0 items-center justify-center rounded-lg text-sidebar-muted transition-colors hover:bg-white/[0.07] hover:text-white"
            disabled
          >
            <LogOut aria-hidden="true" className="size-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
