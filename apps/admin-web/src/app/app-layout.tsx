import { useEffect } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Bell, Menu, Wifi } from "lucide-react";
import { Outlet, useLocation } from "react-router-dom";

import { RoleSwitcher } from "@/components/ui/role-switcher";
import { Sidebar } from "@/components/ui/sidebar";
import { copy } from "@/lib/copy";
import { useUiStore } from "@/lib/ui-store";

export function AppLayout() {
  const location = useLocation();
  const prefersReducedMotion = useReducedMotion();
  const { mobileNavOpen, previewRole, setMobileNavOpen, setPreviewRole } = useUiStore();

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname, setMobileNavOpen]);

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
              className="relative h-full w-fit"
              initial={prefersReducedMotion ? false : { x: -32, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -24, opacity: 0 }}
              transition={{
                duration: prefersReducedMotion ? 0 : 0.22,
                ease: [0.2, 0, 0, 1],
              }}
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
            <RoleSwitcher role={previewRole} onRoleChange={setPreviewRole} />
            <button
              type="button"
              aria-label="Notifications"
              className="relative flex size-10 items-center justify-center rounded-full border border-border bg-surface text-secondary transition-colors duration-standard hover:border-primary-200 hover:bg-primary-50 hover:text-primary-800"
            >
              <Bell aria-hidden="true" className="size-[18px]" />
              <span className="absolute right-2 top-2 size-2 rounded-full border-2 border-white bg-danger" />
            </button>
            <button
              type="button"
              aria-label="Open profile menu"
              className="flex size-10 items-center justify-center rounded-full bg-primary-700 text-xs font-bold text-white shadow-sm transition-colors duration-standard hover:bg-primary-800"
            >
              NM
            </button>
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
