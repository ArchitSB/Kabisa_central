import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useQuery } from "@tanstack/react-query";
import type {
  Cart,
  Customer,
  Product,
  StoreConfig,
  Tokens,
} from "@kabisa/api-client";
import { readGuest, writeGuest } from "./storage";
import { cartItemSchema } from "@kabisa/core";
import { api, queryClient, subscribe, tokens } from "./api";
type GuestItem = {
  product_id: string;
  quantity: number;
  product: Product;
  unit_price: null;
  line_total: null;
};
type Store = {
  authenticated: boolean;
  ready: boolean;
  customer: Customer | undefined;
  config: StoreConfig | undefined;
  cart: Cart;
  add: (product: Product, quantity: number) => Promise<void>;
  change: (id: string, quantity: number) => Promise<void>;
  remove: (id: string) => Promise<void>;
  login: (session: Tokens) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};
const Context = createContext<Store | null>(null);
export function StoreProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [ready, setReady] = useState(false);
  const [guest, setGuest] = useState<GuestItem[]>([]);
  const [guestReady, setGuestReady] = useState(false);
  useEffect(() => {
    void readGuest().then((raw) => {
      if (Array.isArray(raw))
        setGuest(
          raw
            .filter(
              (item) =>
                cartItemSchema.safeParse({
                  product_id: item.product_id,
                  quantity: item.quantity,
                }).success && item.product?.id === item.product_id,
            )
            .slice(0, 100)
            .map((item) => ({
              ...item,
              unit_price: null,
              line_total: null,
              product: { ...item.product, price: null },
            })),
        );
      setGuestReady(true);
    });
  }, []);
  useEffect(() => {
    if (guestReady)
      void writeGuest(guest).catch(() => {
        /* Public basket persistence can be unavailable in private browsing. */
      });
  }, [guest, guestReady]);
  useEffect(() => {
    const sync = () => {
      void tokens.get().then((value) => {
        setAuthenticated(!!value);
        setReady(true);
      });
    };
    sync();
    return subscribe(sync);
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
  });
  const remote = useQuery({
    queryKey: ["cart"],
    queryFn: () => api.get<Cart>("/cart"),
    enabled: authenticated,
    retry: false,
  });
  async function refresh() {
    await queryClient.invalidateQueries();
  }
  async function add(product: Product, quantity: number) {
    if (authenticated) {
      queryClient.setQueryData(
        ["cart"],
        await api.post<Cart>("/cart", { product_id: product.id, quantity }),
      );
    } else
      setGuest((old) => {
        const existing = old.find((i) => i.product_id === product.id);
        return existing
          ? old.map((i) =>
              i.product_id === product.id
                ? { ...i, quantity: Math.min(100000, i.quantity + quantity) }
                : i,
            )
          : [
              ...old,
              {
                product_id: product.id,
                quantity,
                product: { ...product, price: null },
                unit_price: null,
                line_total: null,
              },
            ];
      });
  }
  async function change(id: string, quantity: number) {
    if (authenticated)
      queryClient.setQueryData(
        ["cart"],
        await api.patch<Cart>("/cart", { product_id: id, quantity }),
      );
    else
      setGuest((old) =>
        old.map((i) => (i.product_id === id ? { ...i, quantity } : i)),
      );
  }
  async function remove(id: string) {
    if (authenticated)
      queryClient.setQueryData(["cart"], await api.delete<Cart>(`/cart/${id}`));
    else setGuest((old) => old.filter((i) => i.product_id !== id));
  }
  async function login(session: Tokens) {
    await tokens.set(session);
    if (guest.length) {
      await api.post("/cart/merge", {
        items: guest.map(({ product_id, quantity }) => ({
          product_id,
          quantity,
        })),
      });
      setGuest([]);
    }
    await refresh();
  }
  async function logout() {
    try {
      await api.post("/auth/logout");
    } finally {
      await tokens.set(null);
      queryClient.clear();
    }
  }
  return (
    <Context.Provider
      value={{
        authenticated,
        ready,
        customer: customer.data,
        config: config.data,
        cart: authenticated
          ? remote.data || {
              id: null,
              items: [],
              subtotal: null,
              currency: config.data?.currency || "TZS",
            }
          : {
              id: null,
              items: guest,
              subtotal: null,
              currency: config.data?.currency || "TZS",
            },
        add,
        change,
        remove,
        login,
        logout,
        refresh,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useStore() {
  const value = useContext(Context);
  if (!value) throw new Error("StoreProvider required");
  return value;
}
