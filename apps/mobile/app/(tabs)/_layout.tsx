import { Tabs } from "expo-router";
import Ionicons from "@expo/vector-icons/Ionicons";
import { cartSummary } from "@kabisa/core";
import { useStore } from "../../src/store";
import { colors, t } from "../../src/ui";
const icons: Record<string, keyof typeof Ionicons.glyphMap> = {
  index: "home-outline",
  catalog: "search-outline",
  quick: "flash-outline",
  cart: "bag-outline",
  account: "person-outline",
};
export default function TabLayout() {
  const { cart } = useStore();
  return (
    <Tabs
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.teal,
        tabBarInactiveTintColor: "#68747E",
        tabBarLabelStyle: { fontFamily: "Inter_600SemiBold", fontSize: 9 },
        tabBarStyle: { borderTopColor: "#E2E8E1", paddingTop: 6, height: 66, paddingBottom: 8 },
        tabBarIcon: ({ color, size }) => (
          <Ionicons
            name={icons[route.name] || "ellipse-outline"}
            size={size - 2}
            color={color}
          />
        ),
      })}
    >
      <Tabs.Screen name="index" options={{ title: t("nav.home") }} />
      <Tabs.Screen name="catalog" options={{ title: t("nav.catalog") }} />
      <Tabs.Screen name="quick" options={{ title: t("nav.quick") }} />
      <Tabs.Screen
        name="cart"
        options={{
          title: t("nav.cart"),
          tabBarBadge: cartSummary(cart.items).quantity || undefined,
        }}
      />
      <Tabs.Screen name="account" options={{ title: t("nav.account") }} />
    </Tabs>
  );
}
