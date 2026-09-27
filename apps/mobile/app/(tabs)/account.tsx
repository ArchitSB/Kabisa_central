import { Pressable, View } from "react-native";
import { router } from "expo-router";
import Ionicons from "@expo/vector-icons/Ionicons";
import { useStore } from "../../src/store";
import {
  Action,
  Badge,
  colors,
  ErrorView,
  Heading,
  Panel,
  RequireLogin,
  Screen,
  s,
  t,
  Txt,
} from "../../src/ui";
const sections = [
  ["orders", "cube-outline"],
  ["verification", "shield-checkmark-outline"],
  ["addresses", "location-outline"],
  ["favourites", "heart-outline"],
  ["templates", "bookmark-outline"],
  ["notifications", "notifications-outline"],
  ["profile", "person-outline"],
  ["security", "phone-portrait-outline"],
] as const;
export default function Account() {
  return (
    <RequireLogin>
      <Overview />
    </RequireLogin>
  );
}
function Overview() {
  const { customer, config, logout, refresh } = useStore();
  if (!customer)
    return (
      <Screen>
        <ErrorView error={undefined} retry={() => void refresh()} />
      </Screen>
    );
  return (
    <Screen
      title={t("account.title")}
      eyebrow={customer.customer.business_name}
      body={customer.full_name}
      onRefresh={() => void refresh()}
    >
      <Panel>
        <Badge status={customer.customer.status} />
        <Txt>
          {
            (
              config?.settings.verification_messages as Record<string, string>
            )?.[customer.customer.status]
          }
        </Txt>
        <View style={s.line} />
        <Txt muted>{t("account.tier")}</Txt>
        <Heading>{customer.customer.price_tier}</Heading>
      </Panel>
      <Panel>
        {sections
          .filter(
            ([key]) => key !== "favourites" || config?.settings.enable_wishlist,
          )
          .map(([key, icon]) => (
            <Pressable
              key={key}
              onPress={() => router.push(`/account/${key}`)}
              accessibilityRole="link"
              style={[s.between, { paddingVertical: 12 }]}
            >
              <View style={s.row}>
                <Ionicons name={icon} size={23} color={colors.teal} />
                <Txt>{t(`account.${key}`)}</Txt>
              </View>
              <Ionicons name="chevron-forward" size={17} color={colors.teal} />
            </Pressable>
          ))}
      </Panel>
      <Action
        secondary
        label={t("nav.support")}
        onPress={() => router.push("/pages/contact")}
      />
      <Action
        secondary
        label={t("action.signOut")}
        onPress={async () => {
          await logout();
          router.replace("/");
        }}
      />
    </Screen>
  );
}
