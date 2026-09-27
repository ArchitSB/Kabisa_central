import { useDeferredValue, useEffect, useState } from "react";
import { Pressable, ScrollView, View } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import type { Page, Product } from "@kabisa/api-client";
import { api } from "../../src/api";
import { useStore } from "../../src/store";
import {
  Action,
  Empty,
  ErrorView,
  Input,
  Loading,
  ProductGrid,
  Screen,
  s,
  t,
  Txt,
} from "../../src/ui";
export default function Catalog() {
  const params = useLocalSearchParams<{ category?: string }>();
  const { authenticated } = useStore();
  const [search, setSearch] = useState("");
  const deferred = useDeferredValue(search);
  const [category, setCategory] = useState(params.category || "");
  const [brand, setBrand] = useState("");
  const [stock, setStock] = useState(false);
  const [sort, setSort] = useState("featured");
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState(false);
  useEffect(() => setCategory(params.category || ""), [params.category]);
  useEffect(() => setPage(1), [deferred, category, brand, sort, stock]);
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () =>
      api.get<{ items: { id: string; name: string; slug: string }[] }>(
        "/catalog/categories",
      ),
  });
  const brands = useQuery({
    queryKey: ["brands"],
    queryFn: () =>
      api.get<{ items: { id: string; name: string; slug: string }[] }>(
        "/catalog/brands",
      ),
  });
  const qs = new URLSearchParams({ page: String(page), page_size: "20", sort });
  if (deferred) qs.set("search", deferred);
  if (category) qs.set("category", category);
  if (brand) qs.set("brand", brand);
  if (stock) qs.set("availability", "IN_STOCK");
  const query = useQuery({
    queryKey: ["products", qs.toString(), authenticated],
    queryFn: () => api.get<Page<Product>>("/catalog/products?" + qs),
  });
  return (
    <Screen
      title={t("catalog.title")}
      eyebrow={t("nav.catalog")}
      onRefresh={() => void query.refetch()}
      refreshing={query.isFetching}
    >
      <Input
        label={t("nav.search")}
        value={search}
        onChangeText={setSearch}
        autoCapitalize="none"
        returnKeyType="search"
      />
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: 9 }}
      >
        {[
          { id: "all", name: t("catalog.all"), slug: "" },
          ...(categories.data?.items || []),
        ].map((c) => (
          <Pressable
            key={c.id}
            onPress={() => setCategory(c.slug)}
            style={[s.chip, c.slug === category && s.chipActive]}
            accessibilityState={{ selected: c.slug === category }}
          >
            <Txt>{c.name}</Txt>
          </Pressable>
        ))}
      </ScrollView>
      <View style={s.between}>
        <Txt muted>
          {query.data?.total || 0} {t("catalog.products")}
        </Txt>
        <Action
          label={t("catalog.filters")}
          secondary
          icon="options-outline"
          onPress={() => setFilters(!filters)}
        />
      </View>
      {filters && (
        <View style={s.gap}>
          <Txt>{t("catalog.sort")}</Txt>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {[
              ["featured", "featured"],
              ["name", "name"],
              ["newest", "newest"],
              ...(authenticated
                ? [
                    ["price_asc", "lowPrice"],
                    ["price_desc", "highPrice"],
                  ]
                : []),
            ].map(([value, label]) => (
              <Pressable
                key={value}
                style={[s.chip, sort === value && s.chipActive]}
                onPress={() => setSort(value)}
              >
                <Txt>{t(`catalog.${label}`)}</Txt>
              </Pressable>
            ))}
          </View>
          <Txt>{t("catalog.brand")}</Txt>
          <ScrollView horizontal contentContainerStyle={{ gap: 8 }}>
            {[
              { id: "all", slug: "", name: t("catalog.all") },
              ...(brands.data?.items || []),
            ].map((b) => (
              <Pressable
                key={b.id}
                style={[s.chip, brand === b.slug && s.chipActive]}
                onPress={() => setBrand(b.slug)}
              >
                <Txt>{b.name}</Txt>
              </Pressable>
            ))}
          </ScrollView>
          <Action
            secondary
            label={(stock ? "✓ " : "") + t("status.IN_STOCK")}
            onPress={() => setStock(!stock)}
          />
          <Action
            secondary
            label={t("action.clear")}
            onPress={() => {
              setCategory("");
              setBrand("");
              setStock(false);
              setSort("featured");
              setSearch("");
            }}
          />
        </View>
      )}
      {query.isLoading ? (
        <Loading />
      ) : query.isError ? (
        <ErrorView error={query.error} retry={() => void query.refetch()} />
      ) : query.data?.items.length ? (
        <ProductGrid products={query.data.items} />
      ) : (
        <Empty
          title={t("catalog.noResults")}
          body={t("catalog.noResultsBody")}
        />
      )}
      <View style={s.between}>
        <Action
          secondary
          label={t("catalog.previous")}
          disabled={page <= 1}
          onPress={() => setPage(page - 1)}
        />
        <Txt>
          {page} / {Math.max(1, Math.ceil((query.data?.total || 0) / 20))}
        </Txt>
        <Action
          secondary
          label={t("catalog.next")}
          disabled={page * 20 >= (query.data?.total || 0)}
          onPress={() => setPage(page + 1)}
        />
      </View>
    </Screen>
  );
}
