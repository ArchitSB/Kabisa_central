import { useState } from "react";
import { View } from "react-native";
import { router } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import type { Page, StoreOrder } from "@kabisa/api-client";
import { formatMoney } from "@kabisa/core";
import { api } from "./api";
import {
  Action,
  Badge,
  Empty,
  ErrorView,
  Heading,
  Loading,
  Panel,
  s,
  t,
  Txt,
} from "./ui";
export function OrdersList() {
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["orders", page],
    queryFn: () =>
      api.get<Page<StoreOrder>>(`/orders?page=${page}&page_size=20`),
  });
  return query.isLoading ? (
    <Loading />
  ) : query.isError ? (
    <ErrorView error={query.error} retry={() => void query.refetch()} />
  ) : query.data?.items.length ? (
    <>
      {query.data.items.map((order) => (
        <Panel key={order.id}>
          <Heading>{order.order_number}</Heading>
          <Badge status={order.status} />
          <Txt muted>{new Date(order.created_at).toLocaleDateString()}</Txt>
          <Txt>{formatMoney(order.total_amount, order.currency)}</Txt>
          <Action
            secondary
            label={t("order.detail")}
            onPress={() => router.push(`/orders/${order.id}`)}
          />
        </Panel>
      ))}
      <View style={s.between}>
        <Action
          secondary
          label={t("catalog.previous")}
          disabled={page === 1}
          onPress={() => setPage(page - 1)}
        />
        <Txt>{page}</Txt>
        <Action
          secondary
          label={t("catalog.next")}
          disabled={page * 20 >= query.data.total}
          onPress={() => setPage(page + 1)}
        />
      </View>
    </>
  ) : (
    <Empty
      title={t("order.empty")}
      body={t("order.emptyBody")}
      action={
        <Action
          label={t("action.browse")}
          onPress={() => router.push("/catalog")}
        />
      }
    />
  );
}
