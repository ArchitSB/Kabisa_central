import { useState } from "react";
import { View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import type { Product as ProductType } from "@kabisa/api-client";
import { formatMoney } from "@kabisa/core";
import { api } from "../../src/api";
import { useStore } from "../../src/store";
import {
  Action,
  Badge,
  ErrorView,
  Heading,
  Loading,
  Panel,
  ProductGrid,
  ProductPhoto,
  Quantity,
  Screen,
  s,
  t,
  Txt,
} from "../../src/ui";
export default function Product() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const { authenticated, add, config } = useStore();
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);
  const query = useQuery({
    queryKey: ["product", slug, authenticated],
    queryFn: () =>
      api.get<ProductType & { related: ProductType[] }>(
        `/catalog/products/${slug}`,
      ),
  });
  const product = query.data;
  return (
    <Screen>
      <Action
        secondary
        label={t("action.back")}
        icon="arrow-back-outline"
        onPress={() =>
          router.canGoBack() ? router.back() : router.replace("/catalog")
        }
      />
      {query.isLoading ? (
        <Loading />
      ) : query.isError ? (
        <ErrorView error={query.error} retry={() => void query.refetch()} />
      ) : (
        product && (
          <>
            <ProductPhoto product={product} />
            <Txt muted>
              {product.category.name} · {product.brand?.name}
            </Txt>
            <Heading>{product.name}</Heading>
            <Txt muted>{product.pack_size || product.unit}</Txt>
            <Badge status={product.availability} />
            {product.price ? (
              <Heading>{formatMoney(product.price, product.currency)}</Heading>
            ) : (
              <Action
                label={t("product.priceHidden")}
                onPress={() => router.push("/login")}
              />
            )}
            <View style={s.between}>
              <Quantity
                value={quantity}
                onChange={(n) => {
                  setQuantity(n);
                  setAdded(false);
                }}
              />
              <Action
                label={added ? t("action.added") : t("action.add")}
                disabled={product.availability === "OUT_OF_STOCK"}
                onPress={async () => {
                  await add(product, quantity);
                  setAdded(true);
                }}
              />
            </View>
            {config?.settings.enable_wishlist && (
              <Action
                secondary
                icon="heart-outline"
                label={t("product.favourite")}
                onPress={async () => {
                  if (!authenticated) {
                    router.push("/login");
                    return;
                  }
                  await api.post(`/favourites/${product.id}`);
                }}
              />
            )}
            {product.requires_prescription && (
              <Panel>
                <Txt>{t("product.pom")}</Txt>
                <Txt muted>{t("product.pomBody")}</Txt>
              </Panel>
            )}
            <Panel>
              <Heading>{t("product.details")}</Heading>
              {[
                ["product.generic", product.generic_name],
                ["product.strength", product.strength],
                ["product.pack", product.pack_size],
                ["product.sku", product.sku],
                ["product.registration", product.registration_no],
              ]
                .filter(([, value]) => value)
                .map(([key, value]) => (
                  <View style={s.between} key={key}>
                    <Txt muted>{t(key!)}</Txt>
                    <Txt>{value}</Txt>
                  </View>
                ))}
            </Panel>
            {product.description && (
              <Panel>
                <Heading>{t("product.description")}</Heading>
                <Txt>{product.description}</Txt>
              </Panel>
            )}
            {product.related.length > 0 && (
              <>
                <Heading>{t("product.related")}</Heading>
                <ProductGrid products={product.related} />
              </>
            )}
          </>
        )
      )}
    </Screen>
  );
}
