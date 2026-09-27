import { useEffect, useState } from "react";
import { Platform, Pressable } from "react-native";
import * as SecureStore from "expo-secure-store";
import { router } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import type { Address, Page, StoreOrder } from "@kabisa/api-client";
import { formatMoney } from "@kabisa/core";
import { api, pickUpload, queryClient } from "../src/api";
import { AddressForm } from "../src/forms";
import { useStore } from "../src/store";
import {
  Action,
  Empty,
  ErrorView,
  Heading,
  Input,
  Panel,
  RequireLogin,
  Screen,
  s,
  t,
  Txt,
} from "../src/ui";
type Quote = {
  subtotal: string;
  discount_total: string;
  tax_total: string;
  delivery_fee: string;
  total_amount: string;
  currency: string;
  eta: string | null;
};
const pending = {
  get: async () =>
    Platform.OS === "web"
      ? sessionStorage.getItem("kabisa.checkout")
      : SecureStore.getItemAsync("kabisa.checkout"),
  set: async (value: string | null) => {
    if (Platform.OS === "web") {
      if (value) sessionStorage.setItem("kabisa.checkout", value);
      else sessionStorage.removeItem("kabisa.checkout");
    } else if (value) await SecureStore.setItemAsync("kabisa.checkout", value);
    else await SecureStore.deleteItemAsync("kabisa.checkout");
  },
};
export default function Checkout() {
  return (
    <RequireLogin>
      <CheckoutForm />
    </RequireLogin>
  );
}
function CheckoutForm() {
  const { cart, customer, config } = useStore();
  const addresses = useQuery({
    queryKey: ["addresses"],
    queryFn: () => api.get<Page<Address>>("/addresses"),
  });
  const [address, setAddress] = useState("");
  const [newAddress, setNewAddress] = useState(false);
  const [notes, setNotes] = useState("");
  const [coupon, setCoupon] = useState("");
  const [method, setMethod] = useState("CASH");
  const [document, setDocument] = useState("");
  const [quote, setQuote] = useState<Quote>();
  const [idempotency, setIdempotency] = useState("");
  useEffect(() => {
    if (!address && addresses.data?.items.length)
      setAddress(
        (
          addresses.data.items.find((a) => a.is_default) ||
          addresses.data.items[0]
        ).id,
      );
  }, [addresses.data, address]);
  useEffect(
    () => setQuote(undefined),
    [address, notes, coupon, method, document, cart.subtotal],
  );
  const payload = {
    address_id: address,
    notes: notes || null,
    coupon_code: coupon || null,
    payment_method: method,
    prescription_id: document || null,
  };
  const blocked =
    (config?.settings.require_verification_to_order &&
      customer?.customer.status !== "VERIFIED") ||
    ["SUSPENDED", "REJECTED"].includes(customer?.customer.status || "");
  const pom = cart.items.some((i) => i.product.requires_prescription);
  return (
    <Screen title={t("checkout.title")} body={t("checkout.subtitle")}>
      {blocked ? (
        <Empty
          title={t("checkout.verifiedRequired")}
          body={t("checkout.verifiedBody")}
          action={
            <Action
              label={t("checkout.verification")}
              onPress={() => router.push("/account/verification")}
            />
          }
        />
      ) : !cart.items.length ? (
        <Empty
          title={t("cart.empty")}
          action={
            <Action
              label={t("action.browse")}
              onPress={() => router.replace("/catalog")}
            />
          }
        />
      ) : (
        <>
          <Panel>
            <Heading>{t("checkout.address")}</Heading>
            {addresses.isError && (
              <ErrorView
                error={addresses.error}
                retry={() => void addresses.refetch()}
              />
            )}
            {addresses.data?.items.map((a) => (
              <Pressable
                key={a.id}
                style={[s.chip, a.id === address && s.chipActive]}
                accessibilityRole="radio"
                accessibilityState={{ selected: address === a.id }}
                onPress={() => setAddress(a.id)}
              >
                <Txt>{a.label}</Txt>
                <Txt muted>
                  {a.address}, {a.region}
                </Txt>
              </Pressable>
            ))}
            <Action
              secondary
              label={t("address.add")}
              onPress={() => setNewAddress(!newAddress)}
            />
            {newAddress && (
              <AddressForm
                onSaved={(a) => {
                  setAddress(a.id);
                  setNewAddress(false);
                }}
              />
            )}
            <Input
              label={t("checkout.notes")}
              multiline
              value={notes}
              onChangeText={setNotes}
              maxLength={2000}
            />
          </Panel>
          <Panel>
            <Heading>{t("checkout.payment")}</Heading>
            {["CASH", "MOBILE_MONEY", "BANK_TRANSFER"].map((m) => (
              <Pressable
                key={m}
                style={[s.chip, method === m && s.chipActive]}
                accessibilityRole="radio"
                accessibilityState={{ selected: method === m }}
                onPress={() => setMethod(m)}
              >
                <Txt>{t(`checkout.${m}`)}</Txt>
              </Pressable>
            ))}
            <Txt muted>{t("checkout.manual")}</Txt>
          </Panel>
          {pom && (
            <Panel>
              <Heading>{t("checkout.prescription")}</Heading>
              <Action
                label={document ? t("action.saved") : t("checkout.upload")}
                secondary
                icon="document-attach-outline"
                onPress={async () => {
                  const result = await pickUpload("/prescriptions");
                  if (result) setDocument(result.id);
                }}
              />
            </Panel>
          )}
          <Panel>
            <Heading>{t("cart.summary")}</Heading>
            {cart.items.map((i) => (
              <Txt key={i.product_id}>
                {i.quantity} × {i.product.name}
              </Txt>
            ))}
            <Input
              label={t("checkout.coupon")}
              value={coupon}
              onChangeText={setCoupon}
              maxLength={80}
            />
            {quote && (
              <>
                {[
                  ["cart.subtotal", quote.subtotal],
                  ["cart.discount", quote.discount_total],
                  ["cart.tax", quote.tax_total],
                  ["cart.delivery", quote.delivery_fee],
                ].map(([key, value]) => (
                  <Txt key={key}>
                    {t(key)} · {formatMoney(value, quote.currency)}
                  </Txt>
                ))}
                <Heading>
                  {formatMoney(quote.total_amount, quote.currency)}
                </Heading>
                {quote.eta && <Txt>{quote.eta}</Txt>}
                <Txt muted>{t("checkout.accept")}</Txt>
              </>
            )}
            <Action
              disabled={!address || (pom && !document)}
              label={t(quote ? "checkout.place" : "checkout.review")}
              onPress={async () => {
                if (!quote) {
                  const result = await api.post<Quote>(
                    "/checkout/quote",
                    payload,
                  );
                  const raw = await pending.get();
                  const saved = raw ? JSON.parse(raw) : null;
                  const serialized = JSON.stringify(payload);
                  const key =
                    saved?.payload === serialized
                      ? saved.key
                      : `mobile-${Date.now()}-${Math.random().toString(36).slice(2)}`;
                  await pending.set(
                    JSON.stringify({ key, payload: serialized }),
                  );
                  setIdempotency(key);
                  setQuote(result);
                } else {
                  const order = await api.post<StoreOrder>("/orders", payload, {
                    "Idempotency-Key": idempotency,
                  });
                  await pending.set(null);
                  queryClient.setQueryData(["order", order.id], order);
                  await queryClient.invalidateQueries({ queryKey: ["cart"] });
                  await queryClient.invalidateQueries({ queryKey: ["orders"] });
                  router.replace({
                    pathname: "/orders/[id]",
                    params: { id: order.id, confirmed: "1" },
                  });
                }
              }}
            />
            <Txt muted small>
              {t("checkout.retryNotice")}
            </Txt>
          </Panel>
        </>
      )}
    </Screen>
  );
}
