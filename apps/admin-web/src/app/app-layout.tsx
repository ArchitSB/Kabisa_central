import { useEffect, useRef, type KeyboardEvent } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Menu, ChevronRight, ShieldCheck } from "lucide-react";
import { Outlet, useLocation, Link } from "react-router-dom";

import { WorkspaceSearch } from "@/components/ui/workspace-search";
import { navigation } from "@/lib/navigation";
import { RoleSwitcher } from "@/components/ui/role-switcher";
import { Sidebar } from "@/components/ui/sidebar";
import { useAuthStore } from "@/features/auth/auth-store";
import { copy } from "@/lib/copy";
import { useUiStore } from "@/lib/ui-store";
import { getInitials } from "@/lib/utils";

export function AppLayout() {
  const location = useLocation();
  const section =
    navigation
      .flatMap((s) => s.items)
      .filter((i) => i.href !== "/" && location.pathname.startsWith(i.href))
      .sort((a, b) => b.href.length - a.href.length)[0]?.label || "Overview";
  const prefersReducedMotion = useReducedMotion();
  const user = useAuthStore((state) => state.user);
  const { mobileNavOpen, setMobileNavOpen } = useUiStore();
  const mobileMenuButtonRef = useRef<HTMLButtonElement>(null);
  const mobileNavRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname, setMobileNavOpen]);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const trigger = mobileMenuButtonRef.current;
    const firstControl = mobileNavRef.current?.querySelector<HTMLElement>(
      'button, a[href], [tabindex]:not([tabindex="-1"])',
    );
    firstControl?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      trigger?.focus();
    };
  }, [mobileNavOpen]);

  function handleMobileNavKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      setMobileNavOpen(false);
      return;
    }
    if (event.key !== "Tab") return;
    const controls = Array.from(
      mobileNavRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), a[href], [tabindex]:not([tabindex="-1"])',
      ) ?? [],
    );
    if (controls.length === 0) return;
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="ops-app min-h-screen bg-background">
      <a
        href="#main-content"
        className="fixed left-3 top-3 z-[100] -translate-y-20 rounded-control bg-primary-800 px-4 py-2 text-sm font-semibold text-white transition-transform focus:translate-y-0"
      >
        Skip to content
      </a>

      <div className="hidden lg:block">
        <Sidebar />
      </div>

      <AnimatePresence>
        {mobileNavOpen ? (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.button
              type="button"
              aria-label="Close navigation overlay"
              className="absolute inset-0 cursor-default bg-sidebar/55 backdrop-blur-[2px]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: prefersReducedMotion ? 0 : 0.18 }}
              onClick={() => setMobileNavOpen(false)}
            />
            <motion.div
              ref={mobileNavRef}
              role="dialog"
              aria-modal="true"
              aria-label="Primary navigation"
              tabIndex={-1}
              className="relative h-full w-fit"
              initial={prefersReducedMotion ? false : { x: -32, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -24, opacity: 0 }}
              transition={{
                duration: prefersReducedMotion ? 0 : 0.22,
                ease: [0.2, 0, 0, 1],
              }}
              onKeyDown={handleMobileNavKeyDown}
            >
              <Sidebar mobile onClose={() => setMobileNavOpen(false)} />
            </motion.div>
          </div>
        ) : null}
      </AnimatePresence>

      <div className="ops-workspace">
        <header className="ops-topbar">
          <div className="ops-breadcrumb">
            <button
              ref={mobileMenuButtonRef}
              type="button"
              aria-label={copy.topbar.menu}
              onClick={() => setMobileNavOpen(true)}
              className="ops-menu-toggle"
            >
              <Menu size={20} />
            </button>
            <Link to="/" className="ops-breadcrumb-root">
              Workspace
            </Link>
            <ChevronRight size={14} />
            <span>{section}</span>
          </div>
          <WorkspaceSearch />
          <div className="ops-topbar-actions">
            <RoleSwitcher />
            <span className="ops-access-label">
              <ShieldCheck size={15} /> Staff access
            </span>
            <span
              aria-label={`${user?.name ?? "User"} profile`}
              className="ops-topbar-avatar"
            >
              {getInitials(user?.name ?? "")}
            </span>
          </div>
        </header>

        <main id="main-content" className="ops-main" tabIndex={-1}>
          <motion.div
            key={location.pathname}
            initial={prefersReducedMotion ? false : { opacity: 0.65, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: prefersReducedMotion ? 0 : 0.24, ease: [0.2, 0, 0, 1] }}
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  );
}
