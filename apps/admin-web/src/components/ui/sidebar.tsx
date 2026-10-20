import { useState } from "react";
import { ArrowUpRight, ChevronRight, LogOut, X } from "lucide-react";
import { NavLink } from "react-router-dom";
import { motion, useReducedMotion } from "motion/react";
import { useAuthStore } from "@/features/auth/auth-store";
import { navigation } from "@/lib/navigation";
import { cn, formatRoleName, getInitials } from "@/lib/utils";

export function Sidebar({
  mobile = false,
  onClose,
}: {
  mobile?: boolean;
  onClose?: () => void;
}) {
  const [loggingOut, setLoggingOut] = useState(false);
  const { user, previewRole, hasPermission, logout } = useAuthStore();
  const reduced = useReducedMotion();
  const sections = navigation
    .map((s) => ({
      ...s,
      items: s.items.filter((i) => !i.permission || hasPermission(i.permission)),
    }))
    .filter((s) => s.items.length);
  return (
    <aside
      className={cn("ops-sidebar", mobile && "is-mobile")}
      aria-label="Primary navigation"
    >
      <div className="ops-brand-row">
        <NavLink
          to="/"
          onClick={onClose}
          aria-label="Kabisa Operations home"
          className="ops-logo"
        >
          <img
            src="/images/kabisa-logo.png"
            alt="Kabisa — One step for millions"
            width="150"
            height="68"
          />
        </NavLink>
        {mobile && (
          <button
            className="ops-sidebar-close"
            aria-label="Close navigation"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        )}
      </div>
      <div className="ops-workspace-label">
        <span className="ops-workspace-mark">K</span>
        <div>
          <strong>Operations workspace</strong>
          <span>Administration & fulfilment</span>
        </div>
      </div>
      <nav className="ops-navigation scrollbar-subtle">
        {sections.map((section) => (
          <div className="ops-nav-section" key={section.label}>
            <p>{section.label === "Overview" ? "Your workspace" : section.label}</p>
            {section.items.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                end={item.href === "/" || item.href === "/customers"}
                onClick={onClose}
                className={({ isActive }) => cn("ops-nav-link", isActive && "active")}
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        className="ops-nav-indicator"
                        layoutId={mobile ? "mobile-active-nav" : "active-nav"}
                        transition={{ duration: reduced ? 0 : 0.24, ease: [0.2, 0, 0, 1] }}
                      />
                    )}
                    <item.icon size={18} />
                    <span>{item.label}</span>
                    {isActive && <ChevronRight size={14} />}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="ops-sidebar-bottom">
        <a
          className="ops-store-link"
          href={
            import.meta.env.DEV
              ? `${location.protocol}//${location.hostname}:5174`
              : import.meta.env.VITE_STOREFRONT_URL ||
                "https://storecenter.kabisapharma.com"
          }
          target="_blank"
          rel="noreferrer"
        >
          <span>Visit the storefront</span>
          <ArrowUpRight size={16} />
        </a>
        <div className="ops-user">
          <span className="ops-avatar">{getInitials(user?.name ?? "")}</span>
          <span>
            <strong>{user?.name}</strong>
            <small>{formatRoleName(previewRole?.name ?? user?.role.name ?? "")}</small>
          </span>
          <button
            aria-label="Log out"
            disabled={loggingOut}
            onClick={async () => {
              setLoggingOut(true);
              await logout();
              onClose?.();
            }}
          >
            <LogOut size={17} />
          </button>
        </div>
      </div>
    </aside>
  );
}
