import { en } from "./en";
import { sw } from "./sw";
let locale = localStorage.getItem("kabisa.locale") === "sw" ? "sw" : "en";
const listeners = new Set<() => void>();
export function getLocale() {
  return locale;
}
export function subscribeLocale(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
export function setLocale(value: string) {
  locale = value === "sw" ? "sw" : "en";
  localStorage.setItem("kabisa.locale", locale);
  document.documentElement.lang = locale;
  listeners.forEach((listener) => listener());
}
export function t(key: string): string {
  return (locale === "sw" ? sw[key] : undefined) ?? en[key] ?? key;
}
export function label(value: string) {
  return t(`status.${value}`);
}
document.documentElement.lang = locale;
