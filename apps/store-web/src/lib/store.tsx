import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import type {
  Cart,
  Customer,
  Product,
  StoreConfig,
  Tokens,
} from "@kabisa/api-client";
import { api, queryClient, tokenStore } from "./api";
import { t } from "../i18n";

type GuestItem = {
  product_id: string;
  quantity: number;
  product: Product;
  unit_price: null;
  line_total: null;
};
function readGuest(): GuestItem[] {
  try {
    return JSON.parse(localStorage.getItem("kabisa.guest-cart") || "[]");
  } catch {
    return [];
  }
}
function writeGuest(items: GuestItem[]) {
  localStorage.setItem("kabisa.guest-cart", JSON.stringify(items));
}
type StoreState = {
  customer: Customer | undefined;
  authenticated: boolean;
  config: StoreConfig | undefined;
  cart: Cart;
  loading: boolean;
  add: (product: Product, quantity?: number) => Promise<void>;
  setQuantity: (id: string, quantity: number) => Promise<void>;
  remove: (id: string) => Promise<void>;
  login: (tokens: Tokens) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};
const StoreContext = createContext<StoreState | null>(null);
export function StoreProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(!!tokenStore.get());
  const [guest, setGuest] = useState(readGuest);
  useEffect(() => {
    const sync = () => setAuthenticated(!!tokenStore.get());
    window.addEventListener("kabisa-session", sync);
    return () => window.removeEventListener("kabisa-session", sync);
  }, []);
  const config = useQuery({
    queryKey: ["config"],
    queryFn: () => api.get<StoreConfig>("/config"),
  });
  const customer = useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<Customer>("/me"),
    enabled: authenticated,
    retry: false,
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
  });
  const cart = useQuery({
    queryKey: ["cart"],
    queryFn: () => api.get<Cart>("/cart"),
    enabled: customer.data?.customer.status === "VERIFIED",
    retry: false,
  });
  const refresh = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["cart"] }),
      queryClient.invalidateQueries({ queryKey: ["me"] }),
      queryClient.invalidateQueries({ queryKey: ["orders"] }),
    ]);
  }, []);
  const add = useCallback(
    async (product: Product, quantity = 1) => {
      if (authenticated) {
        const next = await api.post<Cart>("/cart", {
          product_id: product.id,
          quantity,
        });
        queryClient.setQueryData(["cart"], next);
      } else {
        setGuest((previous) => {
          const items = [...previous];
          const index = items.findIndex((i) => i.product_id === product.id);
          if (index >= 0)
            items[index] = {
              ...items[index],
              quantity: Math.min(100000, items[index].quantity + quantity),
            };
          else
            items.push({
              product_id: product.id,
              quantity,
              product: { ...product, price: null },
              unit_price: null,
              line_total: null,
            });
          writeGuest(items);
          return items;
        });
      }
      toast.success(t("action.added"));
    },
    [authenticated],
  );
  const setQuantity = useCallback(
    async (id: string, quantity: number) => {
      if (authenticated) {
        queryClient.setQueryData(
          ["cart"],
          await api.patch<Cart>("/cart", { product_id: id, quantity }),
        );
      } else
        setGuest((previous) => {
          const next = previous.map((i) =>
            i.product_id === id ? { ...i, quantity } : i,
          );
          writeGuest(next);
          return next;
        });
    },
    [authenticated],
  );
  const remove = useCallback(
    async (id: string) => {
      if (authenticated)
        queryClient.setQueryData(
          ["cart"],
          await api.delete<Cart>(`/cart/${id}`),
        );
      else
        setGuest((previous) => {
          const next = previous.filter((i) => i.product_id !== id);
          writeGuest(next);
          return next;
        });
    },
    [authenticated],
  );
  const login = useCallback(async (tokens: Tokens) => {
    tokenStore.set(tokens);
    const profile = await api.get<Customer>("/me");
    queryClient.setQueryData(["me"], profile);
    const items = profile.customer.status === "VERIFIED" ? readGuest() : [];
    if (items.length) {
      try {
        await api.post("/cart/merge", {
          items: items.map(({ product_id, quantity }) => ({
            product_id,
            quantity,
          })),
        });
        writeGuest([]);
        setGuest([]);
      } catch (error) {
        toast.error(
          error instanceof Error ? error.message : t("error.unexpected"),
        );
      }
    }
    await queryClient.invalidateQueries();
  }, []);
  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      tokenStore.set(null);
      queryClient.removeQueries({
        predicate: (q) => !["config"].includes(String(q.queryKey[0])),
      });
    }
  }, []);
  const value = useMemo(
    () => ({
      customer: customer.data,
      authenticated,
      config: config.data,
      cart: authenticated
        ? (cart.data ?? {
            id: null,
            items: [],
            subtotal: null,
            currency: config.data?.currency || "TZS",
          })
        : {
            id: null,
            items: guest,
            subtotal: null,
            currency: config.data?.currency || "TZS",
          },
      loading: customer.isLoading || cart.isLoading,
      add,
      setQuantity,
      remove,
      login,
      logout,
      refresh,
    }),
    [
      customer.data,
      customer.isLoading,
      authenticated,
      config.data,
      cart.data,
      cart.isLoading,
      guest,
      add,
      setQuantity,
      remove,
      login,
      logout,
      refresh,
    ],
  );
  return (
    <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
  );
}
export function useStore() {
  const context = useContext(StoreContext);
  if (!context) throw new Error("StoreProvider is required");
  return context;
}
export function useSetting(key: string): string {
  const { config } = useStore();
  return String(config?.settings[key] ?? "");
}
