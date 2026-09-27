import { Platform } from "react-native";
import * as FileSystem from "expo-file-system/legacy";
// Public guest basket only; identities and private responses never enter this store.
const path = FileSystem.documentDirectory + "kabisa-guest-cart.json";
export async function readGuest(): Promise<unknown> {
  try {
    const raw =
      Platform.OS === "web"
        ? localStorage.getItem("kabisa.mobile.guest")
        : await FileSystem.readAsStringAsync(path);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
export async function writeGuest(value: unknown) {
  const raw = JSON.stringify(value);
  if (Platform.OS === "web") localStorage.setItem("kabisa.mobile.guest", raw);
  else await FileSystem.writeAsStringAsync(path, raw);
}
