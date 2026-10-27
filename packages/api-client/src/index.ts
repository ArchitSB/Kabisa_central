export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
export type Tokens = { access_token: string; refresh_token: string };
export interface TokenProvider {
  get(): Tokens | null | Promise<Tokens | null>;
  set(tokens: Tokens | null): void | Promise<void>;
}
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export interface TransportResponse {
  ok: boolean;
  status: number;
  headers?: { get(name: string): string | null };
  json(): Promise<unknown>;
}
export type Transport = (
  url: string,
  options?: {
    method?: string;
    headers?: Record<string, string>;
    body?: string;
    signal?: AbortSignal;
  },
) => Promise<TransportResponse>;
export function createApiClient(options: {
  baseUrl: string;
  fetch: Transport;
  tokens: TokenProvider;
  timeoutMs?: number;
}) {
  let rotating: Promise<Tokens | null> | null = null;
  const base = options.baseUrl.replace(/\/$/, "");
  const timeoutMs =
    options.timeoutMs &&
    Number.isFinite(options.timeoutMs) &&
    options.timeoutMs > 0
      ? options.timeoutMs
      : 10_000;

  async function send(
    url: string,
    init: NonNullable<Parameters<Transport>[1]>,
    timeout = timeoutMs,
  ): Promise<TransportResponse> {
    const isGet = (init.method ?? "GET").toUpperCase() === "GET";
    for (let attempt = 0; ; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeout);
      try {
        const response = await options.fetch(url, {
          ...init,
          signal: controller.signal,
        });
        const data =
          response.status === 204
            ? undefined
            : await response.json().catch((error: unknown) => {
                if (controller.signal.aborted) throw error;
                return {};
              });
        if (controller.signal.aborted)
          throw new ApiError(
            0,
            "timeout",
            "The server took too long to respond. Please try again.",
          );
        if (
          isGet &&
          attempt === 0 &&
          [502, 503, 504].includes(response.status)
        ) {
          clearTimeout(timer);
          await new Promise((resolve) => setTimeout(resolve, 1500));
          continue;
        }
        return {
          ok: response.ok,
          status: response.status,
          headers: response.headers,
          json: async () => data,
        };
      } catch (error) {
        clearTimeout(timer);
        const failure = controller.signal.aborted
          ? new ApiError(
              0,
              "timeout",
              "The server took too long to respond. Please try again.",
            )
          : error instanceof ApiError
            ? error
            : new ApiError(
                0,
                "network",
                "The API cannot be reached. Check your connection.",
              );
        if (
          isGet &&
          attempt === 0 &&
          ["timeout", "network"].includes(failure.code)
        ) {
          await new Promise((resolve) => setTimeout(resolve, 1500));
          continue;
        }
        throw failure;
      } finally {
        clearTimeout(timer);
      }
    }
  }
  async function decode<T>(response: TransportResponse): Promise<T> {
    if (response.status === 204) return undefined as T;
    const data = (await response.json().catch(() => ({}))) as {
      detail?: string;
      code?: string;
    };
    if (!response.ok)
      throw new ApiError(
        response.status,
        data.code ?? "request_failed",
        response.status === 401
          ? "Your session has expired. Please sign in again."
          : response.status === 403
            ? "You do not have permission to access this content."
            : response.status >= 500
              ? "The server could not complete this request. Please try again shortly."
              : typeof data.detail === "string"
                ? data.detail
                : "We could not complete that request. Please try again.",
        response.headers?.get("X-Request-ID") ?? undefined,
      );
    return data as T;
  }
  async function request<T>(
    path: string,
    init: {
      method?: string;
      body?: unknown;
      headers?: Record<string, string>;
      timeoutMs?: number;
    } = {},
    retried = false,
  ): Promise<T> {
    const tokens = await options.tokens.get();
    const response = await send(
      `${base}${path}`,
      {
        method: init.method ?? "GET",
        headers: {
          "Content-Type": "application/json",
          ...(tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {}),
          ...init.headers,
        },
        ...(init.body !== undefined ? { body: JSON.stringify(init.body) } : {}),
      },
      init.timeoutMs,
    );
    if (
      response.status === 401 &&
      tokens &&
      !retried &&
      !/^\/auth\/(login|otp|register|refresh|password\/reset)(?:\/|$)/.test(
        path,
      )
    ) {
      const latest = await options.tokens.get();
      if (latest && latest.access_token !== tokens.access_token)
        return request<T>(path, init, true);
      rotating ??= (async () => {
        try {
          const r = await send(`${base}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: tokens.refresh_token }),
          });
          const next = await decode<Tokens>(r);
          await options.tokens.set(next);
          return next;
        } catch (error) {
          if (error instanceof ApiError && error.status === 401)
            await options.tokens.set(null);
          throw error;
        } finally {
          rotating = null;
        }
      })();
      await rotating;
      return request<T>(path, init, true);
    }
    return decode<T>(response);
  }
  return {
    request,
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body?: unknown, headers?: Record<string, string>) =>
      request<T>(path, { method: "POST", body, headers }),
    patch: <T>(path: string, body: unknown) =>
      request<T>(path, { method: "PATCH", body }),
    delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  };
}
export type Product = {
  id: string;
  slug: string;
  name: string;
  sku: string;
  generic_name: string | null;
  description: string | null;
  strength: string | null;
  pack_size: string | null;
  unit: string;
  product_type: string;
  category: { id: string; name: string; slug: string };
  brand: { id: string; name: string; slug: string } | null;
  images: string[];
  requires_prescription: boolean;
  registration_no: string | null;
  availability: "IN_STOCK" | "LIMITED" | "OUT_OF_STOCK";
  price: string | null;
  currency: string;
  min_order_quantity: number;
};
export type Cart = {
  id: string | null;
  items: {
    product_id: string;
    quantity: number;
    unit_price: string | null;
    line_total: string | null;
    product: Product;
  }[];
  subtotal: string | null;
  currency: string;
};
export type Content = {
  id: string;
  title?: string;
  subtitle?: string;
  slug?: string;
  image_path?: string;
  mobile_image_path?: string;
  link_url?: string;
  placement?: string;
  body?: string;
  question?: string;
  answer?: string;
  message?: string;
  type?: string;
  author?: string;
  organisation?: string;
  quote?: string;
  label?: string;
  sort_order: number;
  is_active: boolean;
  products?: Product[];
  [key: string]: unknown;
};
export type StoreConfig = {
  currency: string;
  company: Record<string, string>;
  settings: Record<
    string,
    string | number | boolean | Record<string, unknown> | unknown[]
  >;
};
export type StoreHome = {
  config: StoreConfig;
  banners: Content[];
  collections: Content[];
  announcements: Content[];
  testimonials: Content[];
  menus: Content[];
  categories: { id: string; name: string; slug: string; image_path?: string }[];
  brands: { id: string; name: string; slug: string }[];
  featured: Product[];
};
export type Customer = {
  id: string;
  full_name: string;
  phone: string;
  email: string | null;
  customer: {
    id: string;
    business_name: string;
    business_type: string;
    status: string;
    physical_address: string;
    region: string;
    rejection_reason: string | null;
    price_tier: string;
    payment_terms: string;
    credit_limit: string | null;
    credit_balance: string;
  };
  documents: {
    id: string;
    doc_type: string;
    status: string;
    notes: string | null;
    original_filename: string;
  }[];
  missing_documents: string[];
};
export type Address = {
  id: string;
  label: string;
  address: string;
  region: string | null;
  contact_person: string | null;
  phone: string | null;
  is_default: boolean;
};
export type StoreOrder = {
  id: string;
  order_number: string;
  status: string;
  payment_status: string;
  payment_method: string;
  subtotal: string;
  discount_total: string;
  tax_total: string;
  delivery_fee: string;
  total_amount: string;
  balance_due: string;
  currency: string;
  delivery_address: string;
  delivery_status: string | null;
  created_at: string;
  items: {
    product_id: string;
    product_name: string;
    product_sku: string;
    quantity: number;
    unit_price: string;
    line_total: string;
  }[];
  history: { status: string; created_at: string }[];
};
