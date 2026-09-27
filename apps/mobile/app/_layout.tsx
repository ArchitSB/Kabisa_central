import { useEffect, useState } from "react";
import { AccessibilityInfo } from "react-native";
import { Stack } from "expo-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { StatusBar } from "expo-status-bar";
import {
  useFonts,
  Inter_400Regular,
  Inter_600SemiBold,
} from "@expo-google-fonts/inter";
import { Fraunces_500Medium } from "@expo-google-fonts/fraunces";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StoreProvider } from "../src/store";
import { queryClient } from "../src/api";
export default function RootLayout() {
  const [reduced, setReduced] = useState(true);
  useEffect(() => {
    void AccessibilityInfo.isReduceMotionEnabled().then(setReduced);
    const subscription = AccessibilityInfo.addEventListener(
      "reduceMotionChanged",
      setReduced,
    );
    return () => subscription.remove();
  }, []);
  const [loaded, error] = useFonts({
    Inter_400Regular,
    Inter_600SemiBold,
    Fraunces_500Medium,
  });
  if (!loaded && !error) return null;
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <StoreProvider>
          <StatusBar style="dark" />
          <Stack
            screenOptions={{
              headerShown: false,
              contentStyle: { backgroundColor: "#fff" },
              animation: reduced ? "none" : "fade_from_bottom",
            }}
          >
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="login" options={{ presentation: "modal" }} />
          </Stack>
        </StoreProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
