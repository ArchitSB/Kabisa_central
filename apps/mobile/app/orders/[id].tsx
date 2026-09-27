import { useState } from "react";
import { View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import Ionicons from "@expo/vector-icons/Ionicons";
import { useQuery } from "@tanstack/react-query";
import type { StoreOrder } from "@kabisa/api-client";
import { canCancelOrder, formatMoney, orderStages } from "@kabisa/core";
import { api, download } from "../../src/api";
import { useStore } from "../../src/store";
import {
  Action,
  Badge,
  colors,
  ErrorView,
  Heading,
  Loading,
  Panel,
  RequireLogin,
  Screen,
  s,
  t,
  Txt,
} from "../../src/ui";
export default function Order() {
  return (
    <RequireLogin>
      <Detail />
    </RequireLogin>
  );
}
function Detail() {
  const { id, confirmed } = useLocalSearchParams<{
    id: string;
    confirmed?: string;
  }>();
  const { refresh } = useStore();
  const [cancel, setCancel] = useState(false);
  const query = useQuery({
    queryKey: ["order", id],
    queryFn: () => api.get<StoreOrder>(`/orders/${id}`),
    refetchInterval: 30000,
  });
  const order = query.data;
  return (
    <Screen
      title={t(confirmed ? "order.success" : "order.detail")}
      body={confirmed ? t("order.successBody") : undefined}
      onRefresh={() => void query.refetch()}
    >
      {confirmed && (
        <View style={{ alignItems: "center", padding: 20 }}>
          <Ionicons name="checkmark-circle" size={65} color={colors.teal} />
        </View>
      )}
      {query.isLoading ? (
        <Loading />
      ) : query.isError ? (
        <ErrorView error={query.error} retry={() => void query.refetch()} />
      ) : (
        order && (
          <>
            <Panel>
              <Heading>{order.order_number}</Heading>
              <View style={s.row}>
                <Badge status={order.status} />
                <Badge status={order.payment_status} />
              </View>
              <Txt muted>{new Date(order.created_at).toLocaleString()}</Txt>
            </Panel>
            <Panel>
              <Heading>{t("order.progress")}</Heading>
              {orderStages.map((status, index) => {
                const reached = order.history.some((h) => h.status === status);
                return (
                  <View key={status} style={s.row}>
                    <Ionicons
                      name={reached ? "checkmark-circle" : "ellipse-outline"}
                      size={23}
                      color={reached ? colors.teal : "#A7B2AA"}
                    />
                    <Txt>
                      {index + 1}. {t(`status.${status}`)}
                    </Txt>
                  </View>
                );
              })}
              {!orderStages.includes(
                order.status as (typeof orderStages)[number],
              ) && <Badge status={order.status} />}
              {order.delivery_status && (
                <Badge status={order.delivery_status} />
              )}
            </Panel>
            <Panel>
              <Heading>{t("cart.summary")}</Heading>
              {order.items.map((item, index) => (
                <View key={index} style={s.gap}>
                  <Txt>
                    {item.quantity} × {item.product_name}
                  </Txt>
                  <Txt muted>
                    {formatMoney(item.line_total, order.currency)}
                  </Txt>
                  <View style={s.line} />
                </View>
              ))}
              {[
                ["cart.subtotal", order.subtotal],
                ["cart.discount", order.discount_total],
                ["cart.tax", order.tax_total],
                ["cart.delivery", order.delivery_fee],
                ["cart.total", order.total_amount],
                ["order.balance", order.balance_due],
              ].map(([key, value]) => (
                <View style={s.between} key={key}>
                  <Txt muted>{t(key)}</Txt>
                  <Txt>{formatMoney(value, order.currency)}</Txt>
                </View>
              ))}
              <Action
                secondary
                label={t("action.download")}
                icon="download-outline"
                onPress={() =>
                  download(
                    `/orders/${id}/invoice`,
                    `${order.order_number}.xlsx`,
                  )
                }
              />
            </Panel>
            <Panel>
              <Heading>{t("order.deliveryAddress")}</Heading>
              <Txt>{order.delivery_address}</Txt>
              <Txt>{t(`checkout.${order.payment_method}`)}</Txt>
            </Panel>
            <Action
              label={t("order.reorder")}
              onPress={async () => {
                await api.post(`/orders/${id}/reorder`);
                await refresh();
                router.push("/cart");
              }}
            />
            {canCancelOrder(order.status) && (
              <Action
                secondary
                label={t("order.cancel")}
                onPress={() => setCancel(!cancel)}
              />
            )}
            {cancel && (
              <Panel>
                <Txt>{t("order.cancelConfirm")}</Txt>
                <Action
                  label={t("order.cancel")}
                  onPress={async () => {
                    await api.post(`/orders/${id}/cancel`);
                    setCancel(false);
                    await refresh();
                  }}
                />
                <Action
                  secondary
                  label={t("action.back")}
                  onPress={() => setCancel(false)}
                />
              </Panel>
            )}
          </>
        )
      )}
      <Action
        secondary
        label={t("account.orders")}
        onPress={() => router.replace("/account/orders")}
      />
    </Screen>
  );
}
