import careHero from "../../assets/care-hero.webp";
import { Image, Pressable, View } from "react-native";
import { router } from "expo-router";
import Ionicons from "@expo/vector-icons/Ionicons";
import { useQuery } from "@tanstack/react-query";
import type { StoreHome } from "@kabisa/api-client";
import { api, assetUrl } from "../../src/api";
import { useStore } from "../../src/store";
import {
  Action,
  colors,
  Empty,
  ErrorView,
  Heading,
  Loading,
  Panel,
  ProductGrid,
  Screen,
  s,
  t,
  Txt,
} from "../../src/ui";
export default function Home() {
  const { authenticated, customer } = useStore();
  const query = useQuery({
    queryKey: ["home", authenticated],
    queryFn: () => api.get<StoreHome>("/home"),
  });
  const home = query.data;
  const hero = home?.banners.find((b) => b.placement === "HOME_HERO");
  const cfg = home?.config.settings;
  return (
    <Screen>
      <View style={s.between}>
        <View style={s.row}>
          <View
            style={{
              backgroundColor: colors.teal,
              padding: 10,
              borderRadius: 11,
            }}
          >
            <Ionicons name="medical" size={23} color="#fff" />
          </View>
          <Heading>Kabisa.</Heading>
        </View>
        <Pressable
          onPress={() =>
            router.push(authenticated ? "/account/notifications" : "/login")
          }
          accessibilityLabel={
            authenticated ? t("account.notifications") : t("nav.login")
          }
          style={{ padding: 12 }}
        >
          <Ionicons
            name={authenticated ? "notifications-outline" : "person-outline"}
            size={23}
            color={colors.teal}
          />
        </Pressable>
      </View>
      <Pressable
        onPress={() => router.push("/catalog")}
        accessibilityRole="search"
        style={[s.input, s.row]}
      >
        <Ionicons name="search-outline" size={18} color={colors.teal} />
        <Txt muted>{t("nav.search")}</Txt>
      </Pressable>
      {query.isLoading ? (
        <Loading />
      ) : query.isError ? (
        <ErrorView error={query.error} retry={() => void query.refetch()} />
      ) : cfg?.maintenance_mode ? (
        <Empty
          title={t("error.maintenance")}
          body={String(cfg.maintenance_message)}
        />
      ) : (
        <>
          {home?.announcements.map((a) => (
            <Panel key={a.id}>
              <Txt>{a.message}</Txt>
            </Panel>
          ))}
          {hero && (
            <View
              style={{
                backgroundColor: colors.cream,
                borderRadius: 20,
                overflow: "hidden",
              }}
            >
              <View style={{ padding: 25, gap: 18 }}>
                <Txt small muted>
                  {String(cfg?.home_eyebrow || "")}
                </Txt>
                <Heading>{hero.title}</Heading>
                <Txt muted>{hero.subtitle}</Txt>
                <Action
                  label={String(hero.link_label || t("action.browse"))}
                  onPress={() =>
                    router.push(nativePath(hero.link_url || "/catalog"))
                  }
                  icon="arrow-forward-outline"
                />
              </View>
              <Image
                source={
                  hero.image_path?.startsWith("/images/kabisa-care-hero")
                    ? careHero
                    : { uri: assetUrl(hero.image_path) }
                }
                accessibilityLabel={t("home.illustration")}
                style={{ height: 225, width: "100%" }}
                resizeMode="cover"
              />
            </View>
          )}
          {customer && (
            <Panel>
              <Txt>{customer.customer.business_name}</Txt>
              <Txt muted>
                {
                  (cfg?.verification_messages as Record<string, string>)?.[
                    customer.customer.status
                  ]
                }
              </Txt>
            </Panel>
          )}
          <View style={s.between}>
            <Heading>{t("home.browseCare")}</Heading>
            <Pressable onPress={() => router.push("/catalog")}>
              <Ionicons name="arrow-forward" size={23} color={colors.teal} />
            </Pressable>
          </View>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
            {home?.categories.slice(0, 6).map((c) => (
              <Pressable
                key={c.id}
                style={[s.chip, { maxWidth: "100%" }]}
                onPress={() =>
                  router.push({
                    pathname: "/catalog",
                    params: { category: c.slug },
                  })
                }
              >
                <Txt>{c.name}</Txt>
              </Pressable>
            ))}
          </View>
          {home?.collections
            .filter((c) => c.products?.length)
            .map((c) => (
              <View style={s.gap} key={c.id}>
                <Heading>{c.title}</Heading>
                {c.subtitle && <Txt muted>{c.subtitle}</Txt>}
                <ProductGrid products={c.products!.slice(0, 4)} />
              </View>
            ))}
          {!home?.collections.some((c) => c.products?.length) &&
          home?.featured.length ? (
            <ProductGrid products={home.featured.slice(0, 4)} />
          ) : null}
          <View
            style={{
              padding: 25,
              gap: 20,
              backgroundColor: "#E8F2EE",
              borderRadius: 16,
            }}
          >
            <Ionicons name="list-outline" size={34} color={colors.teal} />
            <Heading>{String(cfg?.home_quick_title || "")}</Heading>
            <Txt>{String(cfg?.home_quick_body || "")}</Txt>
            <Action
              label={t("home.quickLink")}
              onPress={() => router.push("/quick")}
            />
          </View>
          <Panel>
            <Heading>{String(cfg?.home_trust_title || "")}</Heading>
            <Txt muted>{String(cfg?.home_trust_body || "")}</Txt>
            <Action
              label={authenticated ? t("nav.account") : t("home.accountLink")}
              secondary
              onPress={() =>
                router.push(authenticated ? "/account" : "/register")
              }
            />
          </Panel>
          <View style={s.row}>
            <Action
              label={t("nav.support")}
              secondary
              onPress={() => router.push("/pages/contact")}
            />
            <Action
              label="FAQ"
              secondary
              onPress={() => router.push("/pages/faqs")}
            />
          </View>
        </>
      )}
    </Screen>
  );
}
function nativePath(path: string) {
  if (path === "/quick-order") return "/quick";
  if (path.startsWith("/catalog")) return path;
  if (path.startsWith("/account") || path === "/register" || path === "/login")
    return path;
  return `/pages/${path.replace(/^\//, "")}`;
}
