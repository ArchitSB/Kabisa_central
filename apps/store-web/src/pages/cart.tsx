import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookmarkPlus, ShoppingBag, Trash2 } from "lucide-react";
import { cartSummary, formatMoney } from "@kabisa/core";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { t } from "../i18n";
import { ProductImage } from "../components/product-card";
import {
  AsyncButton,
  Empty,
  Field,
  PageIntro,
  Quantity,
  TrustNote,
} from "../components/ui";
export default function Basket() {
  const { cart, authenticated, remove, setQuantity } = useStore();
  const [template, setTemplate] = useState(false);
  const [name, setName] = useState("");
  useSeo(t("cart.title"));
  return (
    <div className="container cart-page">
      <PageIntro
        eyebrow={t("nav.cart")}
        title={t("cart.title")}
        body={t("cart.subtitle")}
      />
      {cart.items.length ? (
        <div className="commerce-layout">
          <div>
            <section className="panel basket-lines">
              {cart.items.map((item) => (
                <div className="basket-line" key={item.product_id}>
                  <Link to={`/product/${item.product.slug}`}>
                    <ProductImage product={item.product} />
                  </Link>
                  <div className="basket-line-info">
                    <span className="product-brand">
                      {item.product.brand?.name || item.product.category.name}
                    </span>
                    <Link to={`/product/${item.product.slug}`}>
                      <h3>{item.product.name}</h3>
                    </Link>
                    <p>{item.product.pack_size || item.product.unit}</p>
                    {item.unit_price !== null && (
                      <strong>
                        {formatMoney(item.unit_price, cart.currency)}
                      </strong>
                    )}
                    {item.product.availability === "OUT_OF_STOCK" && (
                      <p className="error-text">{t("cart.unavailable")}</p>
                    )}
                  </div>
                  <div className="basket-line-controls">
                    <Quantity
                      value={item.quantity}
                      onChange={(n) =>
                        void setQuantity(item.product_id, n).catch((e) =>
                          toast.error(e.message),
                        )
                      }
                    />
                    <strong>
                      {item.line_total !== null
                        ? formatMoney(item.line_total, cart.currency)
                        : "—"}
                    </strong>
                    <AsyncButton
                      className="icon-button muted"
                      action={() => remove(item.product_id)}
                    >
                      <Trash2 size={17} />
                      <span className="sr-only">{t("action.remove")}</span>
                    </AsyncButton>
                  </div>
                </div>
              ))}
            </section>
            <div className="basket-secondary">
              <Link className="text-link" to="/catalog">
                {t("cart.keepShopping")}
                <ArrowRight size={17} />
              </Link>
              {authenticated && (
                <button
                  className="text-link"
                  onClick={() => setTemplate(!template)}
                >
                  <BookmarkPlus size={17} />
                  {t("cart.saveTemplate")}
                </button>
              )}
            </div>
            {template && (
              <form
                className="panel template-form"
                onSubmit={(e) => e.preventDefault()}
              >
                <Field label={t("cart.templateName")}>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    maxLength={150}
                  />
                </Field>
                <AsyncButton
                  action={async () => {
                    await api.post("/templates", {
                      name,
                      items: cart.items.map(({ product_id, quantity }) => ({
                        product_id,
                        quantity,
                      })),
                    });
                    toast.success(t("action.saved"));
                    setTemplate(false);
                  }}
                  disabled={!name.trim()}
                >
                  {t("action.save")}
                </AsyncButton>
              </form>
            )}
          </div>
          <aside className="order-summary panel">
            <h2>{t("cart.summary")}</h2>
            <p className="summary-item-count">
              {cartSummary(cart.items).quantity} {t("cart.items")}
            </p>
            <dl>
              <div>
                <dt>{t("cart.subtotal")}</dt>
                <dd>
                  {cart.subtotal !== null
                    ? formatMoney(cart.subtotal, cart.currency)
                    : "—"}
                </dd>
              </div>
              <div>
                <dt>{t("cart.delivery")}</dt>
                <dd className="muted">{t("cart.deliveryLater")}</dd>
              </div>
            </dl>
            {authenticated ? (
              <Link className="btn full" to="/checkout">
                {t("action.checkout")}
                <ArrowRight size={17} />
              </Link>
            ) : (
              <>
                <p className="small muted">{t("cart.signInBody")}</p>
                <Link className="btn full" to="/login?returnTo=%2Fcheckout">
                  {t("cart.signIn")}
                  <ArrowRight size={17} />
                </Link>
              </>
            )}
            <TrustNote>{t("cart.livePrices")}</TrustNote>
          </aside>
        </div>
      ) : (
        <Empty
          title={t("cart.empty")}
          body={t("cart.emptyBody")}
          icon={<ShoppingBag size={35} strokeWidth={1.2} />}
          action={
            <Link className="btn" to="/catalog">
              {t("action.browse")}
              <ArrowRight size={17} />
            </Link>
          }
        />
      )}
    </div>
  );
}
