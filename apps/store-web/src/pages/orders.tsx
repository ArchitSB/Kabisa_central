import { lazy, Suspense } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  Download,
  Package,
  RotateCcw,
  ShoppingBag,
} from "lucide-react";
import type { Page, StoreOrder } from "@kabisa/api-client";
import { canCancelOrder, formatMoney, orderStages } from "@kabisa/core";
import { api, download, queryClient } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { t, label } from "../i18n";
import {
  AsyncButton,
  Badge,
  Empty,
  ErrorState,
  PageIntro,
  Skeleton,
} from "../components/ui";
const SuccessMotion = lazy(() => import("../components/success-motion"));
export function OrdersList() {
  const query = useQuery({
    queryKey: ["orders"],
    queryFn: () => api.get<Page<StoreOrder>>("/orders"),
  });
  if (query.isLoading) return <Skeleton cards={2} />;
  if (query.isError && query.data === undefined)
    return <ErrorState error={query.error} retry={() => query.refetch()} />;
  if (!query.data?.items.length)
    return (
      <Empty
        title={t("order.empty")}
        body={t("order.emptyBody")}
        action={
          <Link className="btn" to="/catalog">
            {t("action.browse")}
          </Link>
        }
      />
    );
  return (
    <div className="order-list">
      {query.data.items.map((order) => (
        <Link
          className="order-list-card panel"
          key={order.id}
          to={`/account/orders/${order.id}`}
        >
          <span className="order-icon">
            <Package size={23} />
          </span>
          <div>
            <strong>{order.order_number}</strong>
            <p>
              {new Date(order.created_at).toLocaleDateString()} ·{" "}
              {order.items.length} {t("cart.items")}
            </p>
          </div>
          <Badge kind={order.status === "DELIVERED" ? "success" : "neutral"}>
            {label(order.status)}
          </Badge>
          <strong>{formatMoney(order.total_amount, order.currency)}</strong>
          <ArrowRight size={18} />
        </Link>
      ))}
    </div>
  );
}
export default function OrderDetail() {
  const { id } = useParams();
  const location = useLocation();
  const confirmation = location.pathname.startsWith("/order-confirmed");
  const { refresh } = useStore();
  const query = useQuery({
    queryKey: ["order", id],
    queryFn: () => api.get<StoreOrder>(`/orders/${id}`),
  });
  const order = query.data;
  useSeo(order?.order_number || t("order.detail"));
  if (query.isLoading)
    return (
      <div className="container section">
        <Skeleton cards={2} />
      </div>
    );
  if ((query.isError && query.data === undefined) || !order)
    return (
      <div className="container">
        <ErrorState error={query.error} retry={() => query.refetch()} />
      </div>
    );
  const stage = orderStages.findIndex((s) => s === order.status);
  return (
    <div className="container order-page">
      {confirmation ? (
        <div className="confirmation-heading">
          <Suspense
            fallback={
              <div className="success-animation">
                <Check size={38} />
              </div>
            }
          >
            <SuccessMotion />
          </Suspense>
          <p className="eyebrow">{order.order_number}</p>
          <h1>{t("order.success")}</h1>
          <p>{t("order.successBody")}</p>
          <Link className="btn" to={`/account/orders/${id}`}>
            {t("order.track")}
            <ArrowRight size={17} />
          </Link>
        </div>
      ) : (
        <PageIntro
          eyebrow={t("order.detail")}
          title={order.order_number}
          body={`${t("order.placed")} ${new Date(order.created_at).toLocaleDateString()}`}
        >
          <Badge kind={order.status === "DELIVERED" ? "success" : "neutral"}>
            {label(order.status)}
          </Badge>
        </PageIntro>
      )}
      <div className="commerce-layout">
        <div>
          <section className="panel">
            <h2>{t("order.progress")}</h2>
            <ol className="order-timeline">
              {orderStages.map((status, i) => {
                const event = order.history.find((h) => h.status === status);
                return (
                  <li key={status} className={i <= stage ? "complete" : ""}>
                    <span>{i < stage ? <Check size={15} /> : i + 1}</span>
                    <div>
                      <strong>{label(status)}</strong>
                      {event && (
                        <p>{new Date(event.created_at).toLocaleString()}</p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
            {stage === -1 && (
              <p className="inline-notice">{label(order.status)}</p>
            )}
            {order.delivery_status && (
              <p className="inline-notice">{label(order.delivery_status)}</p>
            )}
          </section>
          <section className="panel order-products">
            <h2>{t("order.detail")}</h2>
            {order.items.map((item) => (
              <div key={item.product_id}>
                <ShoppingBag size={19} />
                <span>
                  <strong>{item.product_name}</strong>
                  <small>
                    {item.quantity} ×{" "}
                    {formatMoney(item.unit_price, order.currency)}
                  </small>
                </span>
                <strong>{formatMoney(item.line_total, order.currency)}</strong>
              </div>
            ))}
          </section>
          <div className="order-actions">
            <AsyncButton
              className="btn secondary"
              action={async () => {
                await api.post(`/orders/${id}/reorder`);
                await refresh();
              }}
            >
              <RotateCcw size={16} />
              {t("order.reorder")}
            </AsyncButton>
            <AsyncButton
              className="btn secondary"
              action={() =>
                download(`/orders/${id}/invoice`, `${order.order_number}.xlsx`)
              }
            >
              <Download size={16} />
              {t("action.download")}
            </AsyncButton>
            {canCancelOrder(order.status) && (
              <AsyncButton
                className="btn danger"
                action={async () => {
                  if (!window.confirm(t("order.cancelConfirm"))) return;
                  await api.post(`/orders/${id}/cancel`);
                  await queryClient.invalidateQueries({
                    queryKey: ["order", id],
                  });
                  await refresh();
                }}
              >
                {t("order.cancel")}
              </AsyncButton>
            )}
          </div>
        </div>
        <aside>
          <section className="panel order-summary">
            <h2>{t("order.payment")}</h2>
            <Badge
              kind={order.payment_status === "PAID" ? "success" : "warning"}
            >
              {label(order.payment_status)}
            </Badge>
            <dl>
              {[
                ["cart.subtotal", order.subtotal],
                ["cart.discount", order.discount_total],
                ["cart.tax", order.tax_total],
                ["cart.delivery", order.delivery_fee],
                ["cart.total", order.total_amount],
                ["order.balance", order.balance_due],
              ].map(([key, value]) => (
                <div
                  key={key}
                  className={key === "order.balance" ? "grand-total" : ""}
                >
                  <dt>{t(key)}</dt>
                  <dd>{formatMoney(value, order.currency)}</dd>
                </div>
              ))}
            </dl>
            <p className="muted small">
              {t(`checkout.${order.payment_method}`)}
            </p>
          </section>
          <section className="panel delivery-summary">
            <h3>{t("order.deliveryAddress")}</h3>
            <p>{order.delivery_address}</p>
          </section>
        </aside>
      </div>
    </div>
  );
}
