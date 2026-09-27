import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import * as DocumentPicker from "expo-document-picker";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import { createApiClient, type Tokens } from "@kabisa/api-client";
import { QueryClient } from "@tanstack/react-query";
export const apiUrl =
  process.env.EXPO_PUBLIC_API_URL ||
  (Platform.OS === "android"
    ? "http://10.0.2.2:8000/api/v1/store"
    : "http://localhost:8000/api/v1/store");
export const storeUrl =
  process.env.EXPO_PUBLIC_STORE_URL || "http://localhost:5174";
let memory: Tokens | null = null;
const listeners = new Set<() => void>();
export function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
export const tokens = {
  get: async () => {
    if (memory) return memory;
    const raw =
      Platform.OS === "web"
        ? sessionStorage.getItem("kabisa.mobile.session")
        : await SecureStore.getItemAsync("kabisa.session");
    try {
      memory = raw ? JSON.parse(raw) : null;
    } catch {
      memory = null;
    }
    return memory;
  },
  set: async (value: Tokens | null) => {
    memory = value;
    if (Platform.OS === "web") {
      if (value)
        sessionStorage.setItem("kabisa.mobile.session", JSON.stringify(value));
      else sessionStorage.removeItem("kabisa.mobile.session");
    } else {
      if (value)
        await SecureStore.setItemAsync("kabisa.session", JSON.stringify(value));
      else await SecureStore.deleteItemAsync("kabisa.session");
    }
    listeners.forEach((listener) => listener());
  },
};
export const api = createApiClient({
  baseUrl: apiUrl,
  fetch: (url, options) => fetch(url, options),
  tokens,
});
export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30000 } },
});
export function assetUrl(path: string | undefined) {
  if (!path) return undefined;
  if (path.startsWith("https://")) return path;
  return (
    (path.startsWith("/images/") ? storeUrl : apiUrl.split("/api/")[0]) + path
  );
}
export async function pickUpload(
  path: string,
  fields: Record<string, string> = {},
): Promise<{ id: string; original_filename?: string } | null> {
  const result = await DocumentPicker.getDocumentAsync({
    type: ["application/pdf", "image/jpeg", "image/png"],
    copyToCacheDirectory: true,
    multiple: false,
  });
  if (result.canceled) return null;
  const file = result.assets[0];
  if ((file.size || 0) > 10 * 1024 * 1024)
    throw new Error("Maximum file size is 10 MB.");
  await api.get("/me");
  const token = await tokens.get();
  const form = new FormData();
  Object.entries(fields).forEach(([key, value]) => form.append(key, value));
  if (Platform.OS === "web") {
    const blob = await (await fetch(file.uri)).blob();
    form.append("file", blob, file.name);
  } else
    form.append("file", {
      uri: file.uri,
      name: file.name,
      type: file.mimeType || "application/octet-stream",
    } as unknown as Blob);
  const response = await fetch(apiUrl + path, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token.access_token}` } : {},
    body: form,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Upload failed.");
  return data;
}
export async function download(path: string, name: string) {
  await api.get("/me");
  const token = await tokens.get();
  if (!token) throw new Error("Please sign in.");
  if (Platform.OS === "web") {
    const response = await fetch(apiUrl + path, {
      headers: { Authorization: `Bearer ${token.access_token}` },
    });
    if (!response.ok) throw new Error("Download failed.");
    const url = URL.createObjectURL(await response.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return;
  }
  const destination =
    FileSystem.cacheDirectory + name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const result = await FileSystem.downloadAsync(apiUrl + path, destination, {
    headers: { Authorization: `Bearer ${token.access_token}` },
  });
  if (result.status !== 200) throw new Error("Download failed.");
  if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(result.uri);
}
