import { useEffect, useRef, type KeyboardEvent } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Menu, Wifi } from "lucide-react";
import { Outlet, useLocation } from "react-router-dom";

import { RoleSwitcher } from "@/components/ui/role-switcher";
import { Sidebar } from "@/components/ui/sidebar";
import { useAuthStore } from "@/features/auth/auth-store";
import { copy } from "@/lib/copy";
import { useUiStore } from "@/lib/ui-store";
import { getInitials } from "@/lib/utils";

export function AppLayout() {
  const location = useLocation();
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
    const trigger = mobileMenuButtonRef.current;
    const firstControl = mobileNavRef.current?.querySelector<HTMLElement>(
      'button, a[href], [tabindex]:not([tabindex="-1"])',
    );
    firstControl?.focus();
    return () => trigger?.focus();
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
    <div className="min-h-screen bg-background">
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

      <div className="min-h-screen lg:pl-[260px]">
        <header className="sticky top-0 z-20 flex h-[70px] items-center justify-between border-b border-border bg-surface/95 px-4 backdrop-blur-md sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              ref={mobileMenuButtonRef}
              type="button"
              aria-label={copy.topbar.menu}
              onClick={() => setMobileNavOpen(true)}
              className="flex size-10 shrink-0 items-center justify-center rounded-control border border-border bg-surface text-secondary transition-colors duration-standard hover:bg-primary-50 hover:text-primary-800 lg:hidden"
            >
              <Menu aria-hidden="true" className="size-5" />
            </button>
            <div className="hidden items-center gap-2 text-xs font-medium text-secondary sm:flex">
              <span className="flex size-7 items-center justify-center rounded-full bg-success-surface text-success">
                <Wifi aria-hidden="true" className="size-3.5" />
              </span>
              <span>Workspace online</span>
              <span aria-hidden="true" className="text-border">
                /
              </span>
              <span className="rounded-full bg-neutral-surface px-2.5 py-1 text-[11px] font-semibold text-neutral">
                {copy.topbar.preview}
              </span>
            </div>
            <div className="sm:hidden">
              <span className="font-display text-lg font-semibold">Kabisa</span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <RoleSwitcher />
            <div
              aria-label={`${user?.name ?? "User"} profile`}
              role="img"
              className="flex size-10 items-center justify-center rounded-full bg-primary-700 text-xs font-bold text-white shadow-sm"
            >
              {getInitials(user?.name ?? "")}
            </div>
          </div>
        </header>

        <main
          id="main-content"
          className="mx-auto w-full max-w-[1664px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8 xl:px-10 xl:py-9"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
