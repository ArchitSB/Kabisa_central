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
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export interface TransportResponse {
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
}
export type Transport = (
  url: string,
  options?: {
    method?: string;
    headers?: Record<string, string>;
    body?: string;
  },
) => Promise<TransportResponse>;
export function createApiClient(options: {
  baseUrl: string;
  fetch: Transport;
  tokens: TokenProvider;
}) {
  let rotating: Promise<Tokens | null> | null = null;
  const base = options.baseUrl.replace(/\/$/, "");
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
        typeof data.detail === "string"
          ? data.detail
          : "We could not complete that request. Please try again.",
      );
    return data as T;
  }
  async function request<T>(
    path: string,
    init: {
      method?: string;
      body?: unknown;
      headers?: Record<string, string>;
    } = {},
    retried = false,
  ): Promise<T> {
    const tokens = await options.tokens.get();
    const response = await options.fetch(`${base}${path}`, {
      method: init.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        ...(tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {}),
        ...init.headers,
      },
      ...(init.body !== undefined ? { body: JSON.stringify(init.body) } : {}),
    });
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
          const r = await options.fetch(`${base}/auth/refresh`, {
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
