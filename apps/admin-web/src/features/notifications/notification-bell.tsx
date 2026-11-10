import { useEffect, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useInfiniteQuery, useMutation } from "@tanstack/react-query";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  ArrowUpRight,
  Bell,
  CheckCheck,
  ChevronDown,
  ClipboardList,
  CreditCard,
  LoaderCircle,
  PackagePlus,
  Store,
  Truck,
  Warehouse,
  X,
} from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";
import { useLocation, useNavigate } from "react-router-dom";
import { ErrorState } from "@/components/ui/resource-state";
import { useAuthStore } from "@/features/auth/auth-store";
import { describeApiFailure } from "@/lib/api-errors";
import {
  getNotifications,
  markNotificationsOpened,
  type NotificationCursor,
  type StaffNotification,
} from "./notifications-api";

const icons = {
  order: ClipboardList,
  customer: Store,
  payment: CreditCard,
  delivery: Truck,
  product: PackagePlus,
  inventory: Warehouse,
};

export function NotificationBell() {
  const user = useAuthStore((s) => s.user);
  const status = useAuthStore((s) => s.status);
  const preview = useAuthStore((s) => s.previewRole);
  const [open, setOpen] = useState(false);
  const [newAtOpen, setNewAtOpen] = useState<Set<string>>(new Set());
  const [position, setPosition] = useState({ top: 76, right: 16 });
  const trigger = useRef<HTMLButtonElement>(null);
  const opening = useRef(0);
  const navigate = useNavigate();
  const location = useLocation();
  const reduced = useReducedMotion();
  const permissions = [...(user?.permissions ?? [])].sort().join(",");
  const feed = useInfiniteQuery({
    queryKey: ["admin-notifications", user?.id, permissions],
    queryFn: ({ pageParam }) => getNotifications(pageParam),
    initialPageParam: undefined as NotificationCursor,
    getNextPageParam: (page) =>
      page.next_before_at && page.next_before_id
        ? { before_at: page.next_before_at, before_id: page.next_before_id }
        : undefined,
    enabled: status === "authenticated" && !preview,
    staleTime: 10_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
  const opened = useMutation({
    mutationFn: markNotificationsOpened,
    onSuccess: () => {
      void feed.refetch();
    },
  });
  const first = feed.data?.pages[0];
  const unread = first?.unread_count ?? 0;
  const items = Array.from(
    new Map(
      (feed.data?.pages.flatMap((page) => page.items) ?? []).map((item) => [item.id, item]),
    ).values(),
  );

  useEffect(() => {
    opening.current += 1;
    setOpen(false);
  }, [location.key, user?.id, permissions, preview]);

  useEffect(() => {
    if (!open) return;
    const align = () => {
      const rect = trigger.current?.getBoundingClientRect();
      if (rect)
        setPosition({
          top: rect.bottom + 12,
          right: Math.min(
            Math.max(16, window.innerWidth - rect.right),
            window.innerWidth - Math.min(420, window.innerWidth - 32) - 16,
          ),
        });
    };
    align();
    window.addEventListener("resize", align);
    return () => window.removeEventListener("resize", align);
  }, [open]);

  async function show(value: boolean) {
    setOpen(value);
    const attempt = ++opening.current;
    if (!value) return;
    opened.reset();
    setNewAtOpen(new Set());
    const result = await feed.refetch();
    // Opening is acknowledged only after a successful fetch, while still visible.
    if (attempt !== opening.current || result.isError || !result.data) return;
    setNewAtOpen(
      new Set(
        result.data.pages.flatMap((p) => p.items.filter((i) => i.is_new).map((i) => i.id)),
      ),
    );
    opened.mutate(result.data.pages[0].snapshot_at);
  }

  if (status !== "authenticated" || preview) return null;

  return (
    <Dialog.Root open={open} onOpenChange={(value) => void show(value)} modal={false}>
      <Dialog.Trigger asChild>
        <button
          ref={trigger}
          type="button"
          className="relative flex size-10 shrink-0 items-center justify-center rounded-xl border border-border bg-surface text-primary-800 transition-colors hover:border-primary-200 hover:bg-primary-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary-500/20"
          aria-label={
            feed.isError
              ? "Notifications, refresh unavailable"
              : `Notifications, ${unread} new`
          }
          title="Notifications"
        >
          <motion.span
            key={unread > 0 ? "new" : "quiet"}
            initial={false}
            animate={unread && !reduced ? { rotate: [0, -12, 10, -5, 0] } : { rotate: 0 }}
            transition={{ duration: 0.45, ease: "easeOut" }}
            className="flex"
          >
            <Bell size={19} aria-hidden="true" />
          </motion.span>
          <AnimatePresence initial={false} mode="popLayout">
            {unread > 0 && (
              <motion.span
                key={unread}
                className="absolute -right-2 -top-2 flex h-5 min-w-5 items-center justify-center rounded-full border-2 border-surface bg-danger px-1 text-[10px] font-bold tabular-nums text-white shadow-sm"
                initial={reduced ? false : { y: 6, scale: 0.75, opacity: 0 }}
                animate={{ y: 0, scale: 1, opacity: 1 }}
                exit={reduced ? { opacity: 0 } : { y: -6, scale: 0.85, opacity: 0 }}
                transition={{ duration: reduced ? 0 : 0.22, ease: [0.2, 0, 0, 1] }}
                aria-hidden="true"
              >
                {unread > 99 ? "99+" : unread}
              </motion.span>
            )}
          </AnimatePresence>
          {feed.isError && (
            <span
              className="absolute bottom-0 right-0 size-2.5 rounded-full border-2 border-white bg-amber-500"
              aria-hidden="true"
            />
          )}
        </button>
      </Dialog.Trigger>
      <span className="sr-only" role="status" aria-live="polite">
        {first ? `${unread} new notifications` : ""}
      </span>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Content forceMount asChild>
              <motion.div
                style={{
                  top: position.top,
                  right: position.right,
                  maxHeight: `min(600px, calc(100dvh - ${position.top + 16}px))`,
                }}
                className="fixed z-[70] flex w-[min(420px,calc(100vw-32px))] origin-top-right flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-[0_20px_70px_-16px_rgba(16,31,56,0.3)] outline-none"
                initial={reduced ? false : { opacity: 0, y: -8, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: reduced ? 0 : -5, scale: reduced ? 1 : 0.98 }}
                transition={{ duration: reduced ? 0 : 0.2, ease: [0.2, 0, 0, 1] }}
              >
                <div className="flex items-start gap-3 border-b border-border px-5 py-4">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-danger/10 text-danger">
                    <Bell size={19} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <Dialog.Title className="font-display text-lg font-semibold tracking-tight">
                      Notifications
                    </Dialog.Title>
                    <Dialog.Description className="mt-0.5 text-xs text-secondary">
                      Updates for your workspace.
                    </Dialog.Description>
                  </div>
                  <Dialog.Close
                    className="rounded-lg p-2 text-secondary hover:bg-primary-50 focus-visible:ring-2 focus-visible:ring-primary-500"
                    aria-label="Close notifications"
                  >
                    <X size={17} />
                  </Dialog.Close>
                </div>
                <div className="flex items-center justify-between border-b border-border bg-primary-50/50 px-5 py-2.5 text-[11px] font-medium">
                  <span className="flex items-center gap-1.5 text-primary-800">
                    <CheckCheck size={14} />
                    {unread ? `${unread} new since last opened` : "You're up to date"}
                  </span>
                  <span className="text-secondary">Last 30 days</span>
                </div>
                <div
                  className="min-h-0 overflow-y-auto overscroll-contain"
                  aria-busy={feed.isPending}
                >
                  {feed.isPending && (
                    <div
                      role="status"
                      className="flex min-h-40 items-center justify-center gap-2 text-sm text-secondary"
                    >
                      <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" />
                      Loading updates…
                    </div>
                  )}
                  {feed.isError && !first && (
                    <ErrorState
                      title="Notifications could not be loaded"
                      error={feed.error}
                      onRetry={() => void show(true)}
                    />
                  )}
                  {((feed.isError && first) || opened.isError) && (
                    <div
                      role="alert"
                      className="border-b border-border bg-amber-50 px-5 py-3 text-xs text-amber-950"
                    >
                      {opened.isError
                        ? "Your last-opened time wasn't saved. New counts are unchanged."
                        : describeApiFailure(feed.error).message}
                      <button
                        className="ml-2 font-semibold underline"
                        onClick={() => void show(true)}
                      >
                        Try again
                      </button>
                    </div>
                  )}
                  {first && items.length === 0 && (
                    <div className="px-8 py-12 text-center">
                      <CheckCheck className="mx-auto mb-3 size-8 text-primary-300" />
                      <p className="text-sm font-semibold">A clear workspace</p>
                      <p className="mt-2 text-xs leading-5 text-secondary">
                        Order, customer and stock updates you have access to will appear
                        here.
                      </p>
                    </div>
                  )}
                  <ul className="divide-y divide-border" aria-label="Recent notifications">
                    {items.map((item: StaffNotification) => {
                      const Icon = icons[item.kind];
                      const isNew = item.is_new || newAtOpen.has(item.id);
                      return (
                        <li key={item.id}>
                          <button
                            className={`group flex w-full items-start gap-3 px-5 py-4 text-left transition-colors hover:bg-primary-50 focus-visible:bg-primary-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500 ${isNew ? "bg-primary-50/40" : ""}`}
                            onClick={() => {
                              setOpen(false);
                              opening.current += 1;
                              navigate(item.href);
                            }}
                          >
                            <span
                              className={`mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl ${isNew ? "bg-primary-100 text-primary-800" : "bg-background text-secondary"}`}
                            >
                              <Icon size={17} aria-hidden="true" />
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="flex items-center gap-2">
                                <span className="text-[13px] font-semibold leading-5">
                                  {item.title}
                                </span>
                                {isNew && (
                                  <span
                                    className="size-1.5 shrink-0 rounded-full bg-danger"
                                    aria-label="New when opened"
                                  />
                                )}
                              </span>
                              <span className="mt-0.5 block truncate text-xs text-secondary">
                                {item.description}
                              </span>
                              <time
                                className="mt-1.5 block text-[10px] text-secondary"
                                dateTime={item.created_at}
                                title={format(
                                  new Date(item.created_at),
                                  "dd MMM yyyy, HH:mm",
                                )}
                              >
                                {formatDistanceToNow(new Date(item.created_at), {
                                  addSuffix: true,
                                })}
                              </time>
                            </span>
                            <ArrowUpRight
                              size={14}
                              className="mt-1 shrink-0 text-secondary transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 motion-reduce:transform-none"
                              aria-hidden="true"
                            />
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                  {feed.hasNextPage && (
                    <button
                      className="flex w-full items-center justify-center gap-2 border-t border-border py-3 text-xs font-semibold text-primary-800 hover:bg-primary-50 disabled:opacity-50"
                      disabled={feed.isFetchingNextPage}
                      onClick={() => void feed.fetchNextPage()}
                    >
                      {feed.isFetchingNextPage ? (
                        <LoaderCircle size={14} className="animate-spin" />
                      ) : (
                        <ChevronDown size={14} />
                      )}
                      Load earlier updates
                    </button>
                  )}
                </div>
                <p className="border-t border-border px-5 py-3 text-[10px] text-secondary">
                  Opening this panel clears the new count for your account.
                </p>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
