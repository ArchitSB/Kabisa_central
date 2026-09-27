import { useState } from "react";
import { View } from "react-native";
import { router } from "expo-router";
import { formatMoney } from "@kabisa/core";
import { api } from "../../src/api";
import { useStore } from "../../src/store";
import {
  Action,
  Empty,
  Heading,
  Input,
  Panel,
  Quantity,
  Screen,
  s,
  t,
  Txt,
} from "../../src/ui";
export default function Cart() {
  const { cart, authenticated, change, remove, refresh } = useStore();
  const [name, setName] = useState("");
  const [save, setSave] = useState(false);
  return (
    <Screen
      title={t("cart.title")}
      body={t("cart.subtitle")}
      onRefresh={() => void refresh()}
    >
      {!cart.items.length ? (
        <Empty
          title={t("cart.empty")}
          body={t("cart.emptyBody")}
          action={
            <Action
              label={t("action.browse")}
              onPress={() => router.push("/catalog")}
            />
          }
        />
      ) : (
        <>
          {cart.items.map((i) => (
            <Panel key={i.product_id}>
              <Txt>{i.product.name}</Txt>
              <Txt small muted>
                {i.product.sku} · {i.product.pack_size || i.product.unit}
              </Txt>
              <CartQuantity
                id={i.product_id}
                value={i.quantity}
                onChange={change}
              />
              <View style={s.between}>
                <Txt>
                  {i.line_total !== null
                    ? formatMoney(i.line_total, cart.currency)
                    : t("product.priceHidden")}
                </Txt>
                <Action
                  secondary
                  label={t("action.remove")}
                  onPress={() => remove(i.product_id)}
                />
              </View>
            </Panel>
          ))}
          <Panel>
            <Heading>{t("cart.summary")}</Heading>
            <View style={s.between}>
              <Txt>{t("cart.subtotal")}</Txt>
              <Heading>
                {cart.subtotal !== null
                  ? formatMoney(cart.subtotal, cart.currency)
                  : "—"}
              </Heading>
            </View>
            <Txt muted>{t("cart.livePrices")}</Txt>
            <Action
              label={authenticated ? t("action.checkout") : t("cart.signIn")}
              onPress={() =>
                router.push(authenticated ? "/checkout" : "/login")
              }
            />
            {!authenticated && <Txt muted>{t("cart.signInBody")}</Txt>}
          </Panel>
          {authenticated && (
            <>
              <Action
                secondary
                label={t("cart.saveTemplate")}
                onPress={() => setSave(!save)}
              />
              {save && (
                <Panel>
                  <Input
                    label={t("cart.templateName")}
                    value={name}
                    onChangeText={setName}
                    maxLength={150}
                  />
                  <Action
                    label={t("action.save")}
                    disabled={!name.trim()}
                    onPress={async () => {
                      await api.post("/templates", {
                        name,
                        items: cart.items.map(({ product_id, quantity }) => ({
                          product_id,
                          quantity,
                        })),
                      });
                      setName("");
                      setSave(false);
                      router.push("/account/templates");
                    }}
                  />
                </Panel>
              )}
            </>
          )}
        </>
      )}
    </Screen>
  );
}
function CartQuantity({
  id,
  value,
  onChange,
}: {
  id: string;
  value: number;
  onChange: (id: string, n: number) => Promise<void>;
}) {
  const [error, setError] = useState("");
  return (
    <View style={s.gap}>
      <Quantity
        value={value}
        onChange={(n) => {
          setError("");
          void onChange(id, n).catch((e) => setError(e.message));
        }}
      />
      {!!error && <Txt>{error}</Txt>}
    </View>
  );
}
