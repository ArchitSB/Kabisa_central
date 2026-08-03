import type { OrderStatus, PaymentStatus } from "@/features/orders/orders.data";

export type ReportMeta = {
  currency: string;
  generated_at: string;
  company_name: string;
  tin: string | null;
  postal: string | null;
  email: string | null;
  phone: string | null;
};
export type ReportOptions = {
  warehouses: Array<{ id: string; name: string }>;
  categories: Array<{ id: string; name: string }>;
  brands: Array<{ id: string; name: string }>;
  customers: Array<{ id: string; name: string }>;
};
export type Report<TSummary, TRow> = {
  meta: ReportMeta;
  summary: TSummary;
  items: TRow[];
  total: number;
  page: number;
  page_size: number;
};
export type SalesReport = Report<
  {
    customer_count: number;
    order_count: number;
    sales_amount: number;
    today_amount: number;
    collected_amount: number;
    outstanding_amount: number;
  },
  {
    order_id: string;
    order_number: string;
    order_date: string;
    customer_id: string;
    customer_name: string;
    warehouse_id: string;
    warehouse_name: string;
    status: OrderStatus;
    payment_status: PaymentStatus;
    total_amount: number;
    collected_amount: number;
    balance_due: number;
  }
>;
export type ProductsReport = Report<
  {
    sale_quantity: number;
    product_count: number;
    tax_amount: number;
    item_discount: number;
    sale_amount: number;
  },
  {
    product_id: string;
    sku: string;
    name: string;
    brand: string | null;
    category: string;
    hsn_code: string | null;
    quantity_sold: number;
    revenue: number;
    tax: number;
    discount: number;
  }
>;
export type ReceivablesReport = Report<
  {
    customer_count: number;
    order_count: number;
    total_outstanding: number;
    aging: { "0_30": number; "31_60": number; "61_90": number; "90_plus": number };
  },
  {
    order_id: string;
    order_number: string;
    order_date: string;
    customer_id: string;
    customer_name: string;
    payment_status: PaymentStatus;
    total_amount: number;
    collected_amount: number;
    balance_due: number;
    age_days: number;
    aging_bucket: string;
  }
>;
export type InventoryReport = Report<
  {
    stock_value: number;
    low_stock_count: number;
    expiring_soon_count: number;
    dead_stock_count: number;
    cost_missing_count: number;
    dead_stock_window_days: number;
  },
  {
    batch_id: string;
    product_id: string;
    sku: string;
    product_name: string;
    brand: string | null;
    category: string;
    warehouse_id: string;
    warehouse_name: string;
    batch_number: string;
    expiry_date: string;
    on_hand: number;
    cost_price: number | null;
    stock_value: number;
    low_stock: boolean;
    expiring_soon: boolean;
    dead_stock: boolean;
    last_outbound_at: string | null;
  }
>;
export type DashboardMetric = {
  value: number;
  delta_percent: number | null;
  comparison: string;
};
export type DashboardSummary = {
  currency: string;
  generated_at: string;
  orders_today: DashboardMetric | null;
  orders_awaiting_review: number | null;
  sales_today: DashboardMetric | null;
  sales_collected_today: number | null;
  sales_pending_today: number | null;
  active_products: DashboardMetric | null;
  products_awaiting_verification: number | null;
  verified_customers: DashboardMetric | null;
  customers_under_review: number | null;
  low_stock_skus: DashboardMetric | null;
  low_stock_needing_action: number | null;
  expiring_soon: DashboardMetric | null;
  outstanding_receivables: DashboardMetric | null;
  sales_pulse: Array<{ date: string; gross_sales: number }>;
  inventory_watchlist: Array<{
    product_id: string;
    product_name: string;
    sku: string;
    warehouse_id: string;
    warehouse_name: string;
    batch_number: string;
    on_hand: number;
    expiry_date: string;
    alert_type: "LOW_STOCK" | "EXPIRING_SOON";
  }>;
  recent_orders: Array<{
    id: string;
    order_number: string;
    customer_name: string;
    delivery_location: string | null;
    status: OrderStatus;
    payment_status: PaymentStatus;
    total_amount: number;
    created_at: string;
  }>;
};
