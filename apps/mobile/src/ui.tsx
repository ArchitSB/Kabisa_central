import { useState, type ReactNode } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  RefreshControl,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router } from "expo-router";
import { en, formatMoney } from "@kabisa/core";
import { tokens as design } from "@kabisa/design-tokens";
import type { Product } from "@kabisa/api-client";
import { assetUrl } from "./api";
import { useStore } from "./store";
export const t = (key: string) => en[key] || key;
export const colors = {
  ...design.colors,
  teal: design.colors.primary[700],
  ink: design.colors.primary[900],
  cream: design.colors.cream,
};
export function Screen({
  children,
  title,
  eyebrow,
  body,
  refreshing,
  onRefresh,
}: {
  children: ReactNode;
  title?: string;
  eyebrow?: string;
  body?: string;
  refreshing?: boolean;
  onRefresh?: () => void;
}) {
  return (
    <SafeAreaView style={s.safe} edges={["top", "left", "right"]}>
      <KeyboardAvoidingView
        style={s.safe}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={s.screen}
          keyboardShouldPersistTaps="handled"
          refreshControl={
            onRefresh ? (
              <RefreshControl
                refreshing={!!refreshing}
                onRefresh={onRefresh}
                tintColor={colors.teal}
              />
            ) : undefined
          }
        >
          {!!(title || eyebrow) && (
            <View style={s.intro}>
              {!!eyebrow && (
                <Text style={s.eyebrow}>{eyebrow.toUpperCase()}</Text>
              )}
              {!!title && (
                <Text style={s.title} accessibilityRole="header">
                  {title}
                </Text>
              )}
              {!!body && <Text style={s.muted}>{body}</Text>}
              {onRefresh && (
                <Pressable
                  onPress={onRefresh}
                  accessibilityLabel={t("action.retry")}
                >
                  <Ionicons
                    name="refresh-outline"
                    size={20}
                    color={colors.teal}
                  />
                  {refreshing && <ActivityIndicator />}
                </Pressable>
              )}
            </View>
          )}
          {children}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
export function Txt({
  children,
  muted = false,
  small = false,
}: {
  children: ReactNode;
  muted?: boolean;
  small?: boolean;
}) {
  return (
    <Text style={[s.text, muted && s.muted, small && s.small]}>{children}</Text>
  );
}
export function Heading({ children }: { children: ReactNode }) {
  return (
    <Text style={s.heading} accessibilityRole="header">
      {children}
    </Text>
  );
}
export function Panel({ children }: { children: ReactNode }) {
  return <View style={s.panel}>{children}</View>;
}
export function Input({ label, ...props }: TextInputProps & { label: string }) {
  return (
    <View style={s.field}>
      <Text style={s.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor="#68747E"
        {...props}
        style={[
          s.input,
          props.multiline && { minHeight: 110, textAlignVertical: "top" },
          props.style,
        ]}
      />
    </View>
  );
}
export function Action({
  label,
  onPress,
  secondary = false,
  disabled = false,
  icon,
}: {
  label: string;
  onPress: () => void | Promise<unknown>;
  secondary?: boolean;
  disabled?: boolean;
  icon?: keyof typeof Ionicons.glyphMap;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        disabled={disabled || busy}
        onPress={async () => {
          setBusy(true);
          setError("");
          try {
            await onPress();
          } catch (e) {
            setError(e instanceof Error ? e.message : t("error.unexpected"));
          } finally {
            setBusy(false);
          }
        }}
        style={({ pressed }) => [
          s.button,
          secondary && s.secondary,
          (disabled || busy) && { opacity: 0.5 },
          pressed && { opacity: 0.8, transform: [{ scale: 0.99 }] },
        ]}
      >
        {busy ? (
          <ActivityIndicator
            size="small"
            color={secondary ? colors.teal : "#fff"}
          />
        ) : icon ? (
          <Ionicons
            name={icon}
            size={18}
            color={secondary ? colors.teal : "#fff"}
          />
        ) : null}
        <Text style={[s.buttonText, secondary && { color: colors.teal }]}>
          {label}
        </Text>
      </Pressable>
      {!!error && (
        <Text accessibilityRole="alert" style={s.error}>
          {error}
        </Text>
      )}
    </View>
  );
}
export function Empty({
  title,
  body,
  action,
}: {
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <View style={s.empty}>
      <View style={s.emptyIcon}>
        <Ionicons name="leaf-outline" size={36} color={colors.teal} />
      </View>
      <Heading>{title}</Heading>
      {!!body && <Txt muted>{body}</Txt>}
      {action}
    </View>
  );
}
export function Loading() {
  return (
    <View style={s.loading}>
      <ActivityIndicator color={colors.teal} />
      <Txt muted>{t("action.loading")}</Txt>
    </View>
  );
}
export function ErrorView({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  return (
    <Empty
      title={t("error.title")}
      body={error instanceof Error ? error.message : t("error.body")}
      action={
        retry ? (
          <Action label={t("action.retry")} onPress={retry} secondary />
        ) : undefined
      }
    />
  );
}
export function Badge({ status }: { status: string }) {
  return (
    <View
      style={[
        s.badge,
        ["VERIFIED", "DELIVERED", "IN_STOCK", "APPROVED", "PAID"].includes(
          status,
        ) && { backgroundColor: "#E9F9F0" },
      ]}
    >
      <Text style={s.badgeText}>{t(`status.${status}`)}</Text>
    </View>
  );
}
export function Quantity({
  value,
  onChange,
}: {
  value: number;
  onChange: (n: number) => void;
}) {
  return (
    <View style={s.quantity}>
      <Pressable
        disabled={value <= 1}
        onPress={() => onChange(Math.max(1, value - 1))}
        style={s.quantityButton}
        accessibilityLabel={t("product.decrease")}
      >
        <Ionicons name="remove" size={18} color={colors.teal} />
      </Pressable>
      <TextInput
        style={s.quantityInput}
        value={String(value)}
        keyboardType="number-pad"
        accessibilityLabel={t("product.quantity")}
        onChangeText={(text) => {
          const n = Number(text);
          if (Number.isInteger(n) && n >= 1 && n <= 100000) onChange(n);
        }}
      />
      <Pressable
        disabled={value >= 100000}
        onPress={() => onChange(value + 1)}
        style={s.quantityButton}
        accessibilityLabel={t("product.increase")}
      >
        <Ionicons name="add" size={18} color={colors.teal} />
      </Pressable>
    </View>
  );
}
export function ProductPhoto({ product }: { product: Product }) {
  const [failed, setFailed] = useState(false);
  const source = assetUrl(product.images[0]);
  return (
    <View style={s.productImage}>
      {source && !failed ? (
        <Image
          source={{ uri: source }}
          style={{ width: "100%", height: "100%" }}
          resizeMode="contain"
          onError={() => setFailed(true)}
        />
      ) : (
        <>
          <Ionicons name="medkit-outline" size={43} color="#789A93" />
          <Text style={[s.small, { color: "#567E73", marginTop: 12 }]}>
            {product.strength || product.unit}
          </Text>
        </>
      )}
    </View>
  );
}
export function ProductCard({ product }: { product: Product }) {
  const { add } = useStore();
  return (
    <View style={s.productCard}>
      <Pressable
        onPress={() => router.push(`/product/${product.slug}`)}
        accessibilityRole="link"
      >
        <ProductPhoto product={product} />
        <View style={s.productInfo}>
          <Text style={s.eyebrow} numberOfLines={1}>
            {product.brand?.name || product.category.name}
          </Text>
          <Text style={s.productName} numberOfLines={2}>
            {product.name}
          </Text>
          <Txt small muted>
            {product.pack_size || product.unit}
          </Txt>
          <Badge status={product.availability} />
        </View>
      </Pressable>
      <View style={s.productFoot}>
        {product.price ? (
          <Text style={s.price}>
            {formatMoney(product.price, product.currency)}
          </Text>
        ) : (
          <Pressable onPress={() => router.push("/login")}>
            <Text style={[s.small, { color: colors.teal, maxWidth: 100 }]}>
              {t("product.priceHidden")}
            </Text>
          </Pressable>
        )}
        <Pressable
          disabled={product.availability === "OUT_OF_STOCK"}
          accessibilityLabel={t("action.add")}
          onPress={() =>
            void add(product, 1)
              .then(() => Alert.alert(t("action.added"), product.name))
              .catch((e) => Alert.alert(t("error.title"), e.message))
          }
          style={s.add}
        >
          <Ionicons name="add" color={colors.teal} size={20} />
        </Pressable>
      </View>
    </View>
  );
}
export function ProductGrid({ products }: { products: Product[] }) {
  return (
    <View style={s.productGrid}>
      {products.map((product) => (
        <ProductCard product={product} key={product.id} />
      ))}
    </View>
  );
}
export function RequireLogin({ children }: { children: ReactNode }) {
  const { authenticated, ready } = useStore();
  if (!ready) return <Loading />;
  return authenticated ? (
    <>{children}</>
  ) : (
    <Screen>
      <Empty
        title={t("auth.welcome")}
        body={t("auth.loginBody")}
        action={
          <Action
            label={t("nav.login")}
            onPress={() => router.push("/login")}
          />
        }
      />
    </Screen>
  );
}
export const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#fff" },
  screen: {
    padding: 22,
    paddingBottom: 40,
    gap: 20,
    maxWidth: 800,
    width: "100%",
    alignSelf: "center",
  },
  intro: { gap: 12, marginTop: 10, marginBottom: 5 },
  eyebrow: {
    fontFamily: "Inter_600SemiBold",
    fontSize: 9,
    letterSpacing: 1.2,
    color: colors.teal,
    lineHeight: 16,
    textTransform: "uppercase",
  },
  title: {
    fontFamily: "Fraunces_500Medium",
    fontSize: 36,
    lineHeight: 41,
    letterSpacing: -1.2,
    color: colors.ink,
  },
  heading: {
    fontFamily: "Fraunces_500Medium",
    fontSize: 25,
    lineHeight: 31,
    letterSpacing: -0.5,
    color: colors.ink,
  },
  text: {
    fontFamily: "Inter_400Regular",
    fontSize: 13,
    lineHeight: 22,
    color: colors.text,
  },
  muted: {
    fontFamily: "Inter_400Regular",
    fontSize: 12,
    lineHeight: 21,
    color: colors.secondary,
  },
  small: { fontSize: 10, lineHeight: 17 },
  label: { fontFamily: "Inter_600SemiBold", fontSize: 12, color: colors.ink },
  field: { gap: 9 },
  input: {
    fontFamily: "Inter_400Regular",
    fontSize: 14,
    color: colors.text,
    borderWidth: 1,
    borderColor: "#DCE4DE",
    borderRadius: 9,
    paddingHorizontal: 14,
    paddingVertical: 13,
    minHeight: 48,
    backgroundColor: "#fff",
  },
  button: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 20,
    paddingVertical: 14,
    minHeight: 49,
    borderRadius: 9,
    backgroundColor: colors.teal,
    borderWidth: 1,
    borderColor: colors.teal,
  },
  buttonText: { fontFamily: "Inter_600SemiBold", fontSize: 12, color: "#fff" },
  secondary: { backgroundColor: "#fff", borderColor: "#DCE4DE" },
  panel: {
    padding: 20,
    borderWidth: 1,
    borderColor: "#E2E8E1",
    borderRadius: 13,
    gap: 18,
    backgroundColor: "#fff",
  },
  empty: { paddingVertical: 42, gap: 18, alignItems: "center" },
  emptyIcon: {
    backgroundColor: "#EFF6EF",
    padding: 23,
    borderRadius: 50,
    marginBottom: 12,
  },
  loading: { padding: 30, alignItems: "center", gap: 13 },
  error: {
    fontFamily: "Inter_400Regular",
    fontSize: 12,
    lineHeight: 20,
    color: colors.danger,
    marginTop: 12,
  },
  badge: {
    alignSelf: "flex-start",
    paddingVertical: 5,
    paddingHorizontal: 8,
    backgroundColor: "#F1F3EE",
    borderRadius: 5,
  },
  badgeText: { fontFamily: "Inter_600SemiBold", fontSize: 9, color: "#366951" },
  productGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  productCard: {
    width: "48%",
    borderWidth: 1,
    borderColor: "#E2E8E1",
    borderRadius: 11,
    overflow: "hidden",
    backgroundColor: "#fff",
  },
  productImage: {
    height: 150,
    backgroundColor: "#F4F7F0",
    alignItems: "center",
    justifyContent: "center",
    margin: 6,
    borderRadius: 7,
    padding: 12,
  },
  productInfo: { padding: 12, gap: 8 },
  productName: {
    fontFamily: "Inter_600SemiBold",
    fontSize: 12,
    lineHeight: 18,
    color: colors.text,
    minHeight: 36,
  },
  productFoot: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 7,
    marginHorizontal: 12,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: "#E7ECE5",
  },
  price: {
    fontFamily: "Inter_600SemiBold",
    fontSize: 11,
    color: colors.ink,
    flexShrink: 1,
  },
  add: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 6,
    backgroundColor: "#EAF3EF",
  },
  quantity: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#DCE4DE",
    borderRadius: 7,
    alignSelf: "flex-start",
    overflow: "hidden",
  },
  quantityButton: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  quantityInput: {
    width: 40,
    textAlign: "center",
    fontFamily: "Inter_600SemiBold",
    fontSize: 12,
    color: colors.ink,
  },
  row: { flexDirection: "row", alignItems: "center", gap: 12 },
  between: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 15,
  },
  line: { height: 1, backgroundColor: "#E2E8E1" },
  chip: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#DCE5DA",
    backgroundColor: "#F9FBF7",
  },
  chipActive: { borderColor: colors.teal, backgroundColor: "#E7F1EC" },
  gap: { gap: 17 },
});
