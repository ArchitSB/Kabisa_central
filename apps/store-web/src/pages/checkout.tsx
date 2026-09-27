import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Banknote,
  Building2,
  FileCheck2,
  LockKeyhole,
  MapPin,
  Plus,
  Smartphone,
} from "lucide-react";
import type { Address, Page, StoreOrder } from "@kabisa/api-client";
import { formatMoney } from "@kabisa/core";
import { api, queryClient, upload } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { t } from "../i18n";
import { AddressForm } from "../components/address-form";
import {
  AsyncButton,
  Empty,
  Field,
  PageIntro,
  TrustNote,
} from "../components/ui";
type Quote = {
  subtotal: string;
  discount_total: string;
  tax_total: string;
  delivery_fee: string;
  total_amount: string;
  currency: string;
  eta: string | null;
};
export default function Checkout() {
  const { customer, cart, config } = useStore();
  const navigate = useNavigate();
  const [address, setAddress] = useState("");
  const [newAddress, setNewAddress] = useState(false);
  const [notes, setNotes] = useState("");
  const [method, setMethod] = useState("CASH");
  const [coupon, setCoupon] = useState("");
  const [prescription, setPrescription] = useState("");
  const [fileName, setFileName] = useState("");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [error, setError] = useState("");
  const [key, setKey] = useState(
    () => sessionStorage.getItem("kabisa.checkout.key") || crypto.randomUUID(),
  );
  useSeo(t("action.checkout"));
  const addresses = useQuery({
    queryKey: ["addresses"],
    queryFn: () => api.get<Page<Address>>("/addresses"),
  });
  useEffect(() => {
    if (!address && addresses.data?.items.length)
      setAddress(
        (
          addresses.data.items.find((a) => a.is_default) ||
          addresses.data.items[0]
        ).id,
      );
  }, [address, addresses.data]);
  useEffect(() => {
    setQuote(null);
  }, [address, notes, method, coupon, prescription, cart.subtotal]);
  const payload = {
    address_id: address,
    notes: notes || null,
    payment_method: method,
    coupon_code: coupon.trim() || null,
    prescription_id: prescription || null,
  };
  const requiresPrescription = cart.items.some(
    (i) => i.product.requires_prescription,
  );
  const gated =
    (customer?.customer.status !== "VERIFIED" &&
      config?.settings.require_verification_to_order) ||
    ["REJECTED", "SUSPENDED"].includes(customer?.customer.status || "");
  async function review() {
    setError("");
    try {
      const result = await api.post<Quote>("/checkout/quote", payload);
      const serialized = JSON.stringify(payload);
      if (sessionStorage.getItem("kabisa.checkout.payload") !== serialized) {
        const next = crypto.randomUUID();
        setKey(next);
        sessionStorage.setItem("kabisa.checkout.key", next);
        sessionStorage.setItem("kabisa.checkout.payload", serialized);
      } else sessionStorage.setItem("kabisa.checkout.key", key);
      setQuote(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error.unexpected"));
    }
  }
  async function place() {
    setError("");
    try {
      const result = await api.post<StoreOrder>("/orders", payload, {
        "Idempotency-Key": key,
      });
      sessionStorage.removeItem("kabisa.checkout.key");
      sessionStorage.removeItem("kabisa.checkout.payload");
      queryClient.setQueryData(["order", result.id], result);
      await queryClient.invalidateQueries({ queryKey: ["cart"] });
      await queryClient.invalidateQueries({ queryKey: ["orders"] });
      navigate(`/order-confirmed/${result.id}`, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error.unexpected"));
    }
  }
  return (
    <div className="container checkout-page">
      <PageIntro
        eyebrow={t("action.checkout")}
        title={t("checkout.title")}
        body={t("checkout.subtitle")}
      />
      {gated ? (
        <Empty
          title={t("checkout.verifiedRequired")}
          body={t("checkout.verifiedBody")}
          icon={<FileCheck2 size={35} />}
          action={
            <Link className="btn" to="/account/verification">
              {t("checkout.verification")}
              <ArrowRight size={17} />
            </Link>
          }
        />
      ) : !cart.items.length ? (
        <Empty
          title={t("cart.empty")}
          action={
            <Link className="btn" to="/catalog">
              {t("action.browse")}
            </Link>
          }
        />
      ) : (
        <div className="commerce-layout">
          <div className="checkout-steps">
            <section className="panel">
              <h2>
                <span className="step-number">1</span>
                {t("checkout.address")}
              </h2>
              <div className="address-choice-grid">
                {addresses.data?.items.map((a) => (
                  <label
                    key={a.id}
                    className={`address-choice ${address === a.id ? "selected" : ""}`}
                  >
                    <input
                      type="radio"
                      name="address"
                      value={a.id}
                      checked={address === a.id}
                      onChange={() => setAddress(a.id)}
                    />
                    <MapPin size={20} />
                    <div>
                      <strong>{a.label}</strong>
                      <p>{a.address}</p>
                      <small>{a.region}</small>
                    </div>
                  </label>
                ))}
              </div>
              <button
                className="text-link"
                onClick={() => setNewAddress(!newAddress)}
              >
                <Plus size={17} />
                {t("checkout.newAddress")}
              </button>
              {newAddress && (
                <AddressForm
                  onSaved={(a) => {
                    setAddress(a.id);
                    setNewAddress(false);
                  }}
                />
              )}
              <Field label={t("checkout.notes")}>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder={t("checkout.notesHint")}
                  maxLength={2000}
                />
              </Field>
            </section>
            <section className="panel">
              <h2>
                <span className="step-number">2</span>
                {t("checkout.payment")}
              </h2>
              <div className="payment-methods">
                {[
                  { id: "CASH", icon: Banknote },
                  { id: "MOBILE_MONEY", icon: Smartphone },
                  { id: "BANK_TRANSFER", icon: Building2 },
                ].map(({ id, icon: Icon }) => (
                  <label
                    className={`payment-choice ${method === id ? "selected" : ""}`}
                    key={id}
                  >
                    <input
                      type="radio"
                      name="payment"
                      checked={method === id}
                      onChange={() => setMethod(id)}
                    />
                    <Icon size={23} strokeWidth={1.4} />
                    <span>{t(`checkout.${id}`)}</span>
                  </label>
                ))}
              </div>
              <p className="muted small">{t("checkout.manual")}</p>
            </section>
            {requiresPrescription && (
              <section className="panel">
                <h2>
                  <FileCheck2 size={21} />
                  {t("checkout.prescription")}
                </h2>
                <Field label={t("checkout.upload")}>
                  <input
                    type="file"
                    accept="application/pdf,image/jpeg,image/png"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      setError("");
                      if (file.size > 10 * 1024 * 1024) {
                        setError(t("checkout.upload"));
                        return;
                      }
                      try {
                        const form = new FormData();
                        form.append("file", file);
                        const result = await upload<{ id: string }>(
                          "/prescriptions",
                          form,
                        );
                        setPrescription(result.id);
                        setFileName(file.name);
                      } catch (e) {
                        setError(
                          e instanceof Error
                            ? e.message
                            : t("error.unexpected"),
                        );
                      }
                    }}
                  />
                </Field>
                {fileName && <p className="success-text">{fileName}</p>}
              </section>
            )}
          </div>
          <aside className="order-summary panel">
            <h2>{quote ? t("checkout.quoted") : t("cart.summary")}</h2>
            <div className="checkout-mini-lines">
              {cart.items.map((i) => (
                <div key={i.product_id}>
                  <span>
                    {i.quantity} × {i.product.name}
                  </span>
                  <strong>
                    {i.line_total !== null
                      ? formatMoney(i.line_total, cart.currency)
                      : "—"}
                  </strong>
                </div>
              ))}
            </div>
            <Field label={t("checkout.coupon")}>
              <input
                value={coupon}
                maxLength={80}
                onChange={(e) => setCoupon(e.target.value)}
              />
            </Field>
            <dl>
              {(quote
                ? [
                    ["cart.subtotal", quote.subtotal],
                    ["cart.discount", quote.discount_total],
                    ["cart.tax", quote.tax_total],
                    ["cart.delivery", quote.delivery_fee],
                  ]
                : [["cart.subtotal", cart.subtotal]]
              ).map(([label, value]) => (
                <div key={label}>
                  <dt>{t(label!)}</dt>
                  <dd>
                    {value !== null ? formatMoney(value!, cart.currency) : "—"}
                  </dd>
                </div>
              ))}
              {quote && (
                <div className="grand-total">
                  <dt>{t("cart.total")}</dt>
                  <dd>{formatMoney(quote.total_amount, quote.currency)}</dd>
                </div>
              )}
            </dl>
            {quote?.eta && <p className="inline-notice">{quote.eta}</p>}
            {error && (
              <p className="error-box" role="alert">
                {error}
              </p>
            )}
            {quote ? (
              <>
                <p className="muted small">{t("checkout.accept")}</p>
                <AsyncButton className="btn full" action={place}>
                  {t("checkout.place")}
                  <ArrowRight size={17} />
                </AsyncButton>
              </>
            ) : (
              <AsyncButton
                className="btn full"
                action={review}
                disabled={!address || (requiresPrescription && !prescription)}
              >
                {t("checkout.review")}
                <ArrowRight size={17} />
              </AsyncButton>
            )}
            <TrustNote>
              <LockKeyhole size={15} />
              {t("checkout.secure")}
            </TrustNote>
            <p className="muted micro">{t("checkout.retryNotice")}</p>
          </aside>
        </div>
      )}
    </div>
  );
}
