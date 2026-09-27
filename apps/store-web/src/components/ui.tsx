import { Component, useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Minus,
  Plus,
  PackageOpen,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { t } from "../i18n";
export { Button } from "@kabisa/ui-web";
export function Quantity({
  value,
  onChange,
  disabled = false,
}: {
  value: number;
  onChange: (n: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="quantity">
      <button
        type="button"
        disabled={disabled || value <= 1}
        onClick={() => onChange(Math.max(1, value - 1))}
        aria-label={t("product.decrease")}
      >
        <Minus size={14} />
      </button>
      <input
        aria-label={t("product.quantity")}
        type="number"
        min={1}
        max={100000}
        value={value}
        disabled={disabled}
        onChange={(e) => {
          const n = Number(e.target.value);
          if (Number.isInteger(n) && n >= 1 && n <= 100000) onChange(n);
        }}
      />
      <button
        type="button"
        disabled={disabled || value >= 100000}
        onClick={() => onChange(Math.min(100000, value + 1))}
        aria-label={t("product.increase")}
      >
        <Plus size={14} />
      </button>
    </div>
  );
}
export function Empty({
  title,
  body,
  action,
  icon,
}: {
  title: string;
  body?: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        {icon ?? <PackageOpen size={34} strokeWidth={1.3} />}
      </div>
      <h2>{title}</h2>
      {body && <p>{body}</p>}
      {action}
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error?: unknown;
  retry?: () => void;
}) {
  return (
    <div role="alert">
      <Empty
        title={t("error.title")}
        body={error instanceof Error ? error.message : t("error.body")}
        icon={<RefreshCw size={30} />}
        action={
          retry ? (
            <button className="btn secondary" onClick={retry}>
              {t("action.retry")}
            </button>
          ) : (
            <Link className="btn" to="/">
              {t("page.backHome")}
            </Link>
          )
        }
      />
    </div>
  );
}
export function Skeleton({ cards = 4 }: { cards?: number }) {
  return (
    <div
      className="product-grid"
      role="status"
      aria-label={t("action.loading")}
    >
      {Array.from({ length: cards }, (_, i) => (
        <div key={i} className="skeleton-card">
          <div className="skeleton image" />
          <div className="skeleton line" />
          <div className="skeleton line short" />
        </div>
      ))}
    </div>
  );
}
export function PageIntro({
  eyebrow,
  title,
  body,
  children,
}: {
  eyebrow?: string;
  title: string;
  body?: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-intro">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <div>
        <div>
          <h1>{title}</h1>
          {body && <p>{body}</p>}
        </div>
        {children}
      </div>
    </div>
  );
}
export function SectionHeading({
  eyebrow,
  title,
  body,
  to,
}: {
  eyebrow?: string;
  title: string;
  body?: string;
  to?: string;
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
        {body && <p>{body}</p>}
      </div>
      {to && (
        <Link className="text-link" to={to}>
          {t("action.viewAll")}
          <ArrowRight size={17} />
        </Link>
      )}
    </div>
  );
}
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function Badge({
  children,
  kind = "neutral",
}: {
  children: ReactNode;
  kind?: string;
}) {
  return (
    <span className={`badge ${kind}`}>
      <span className="badge-dot" />
      {children}
    </span>
  );
}
export function TrustNote({ children }: { children: ReactNode }) {
  return (
    <div className="trust-note">
      <ShieldCheck size={18} />
      <span>{children}</span>
    </div>
  );
}
export function AsyncButton({
  children,
  action,
  className = "btn",
  disabled = false,
}: {
  children: ReactNode;
  action: () => Promise<unknown>;
  className?: string;
  disabled?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      className={className}
      disabled={disabled || busy}
      aria-busy={busy}
      onClick={async () => {
        setBusy(true);
        try {
          await action();
        } catch (error) {
          toast.error(
            error instanceof Error ? error.message : t("error.unexpected"),
          );
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? <span className="loading-dot" /> : null}
      {children}
    </button>
  );
}
export function OfflineNotice() {
  const [offline, setOffline] = useState(!navigator.onLine);
  useEffect(() => {
    const sync = () => setOffline(!navigator.onLine);
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, []);
  return offline ? (
    <div className="offline-notice" role="status">
      {t("error.offline")}
    </div>
  ) : null;
}
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    /* Errors are shown without sending customer data to third parties. */
  }
  render() {
    return this.state.failed ? (
      <ErrorState retry={() => this.setState({ failed: false })} />
    ) : (
      this.props.children
    );
  }
}
