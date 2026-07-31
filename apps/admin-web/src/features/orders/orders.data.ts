export type OrderStatus =
  | "PENDING"
  | "APPROVED"
  | "PENDING_DELIVERY"
  | "DELIVERED"
  | "FAILED"
  | "UNFOUND"
  | "CANCELLED";
export type PaymentStatus = "UNPAID" | "PARTIAL" | "PAID";
export type PaymentMethod = "CASH" | "MOBILE_MONEY" | "BANK_TRANSFER" | "OTHER";
export type PaymentRecordStatus = "PENDING" | "COLLECTED" | "FAILED";
export type DeliveryStatus =
  "NOT_ASSIGNED" | "ASSIGNED" | "OUT_FOR_DELIVERY" | "DELIVERED" | "FAILED";
export type VehicleType = "MOTORCYCLE" | "TRUCK" | "VAN" | "OTHER";

export type OrderSummary = {
  id: string;
  order_number: string;
  customer_id: string;
  customer_name: string;
  warehouse_id: string;
  warehouse_name: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  source: "ADMIN" | "CUSTOMER";
  price_tier_id: string;
  price_tier_code: string;
  subtotal: number;
  discount_total: number;
  tax_total: number;
  total_amount: number;
  delivery_address: string | null;
  delivery_location: string | null;
  notes: string | null;
  approved_by: string | null;
  approved_at: string | null;
  item_count: number;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
};

export type Allocation = {
  id: string;
  batch_id: string;
  batch_number: string;
  warehouse_id: string;
  warehouse_name: string;
  quantity: number;
  expiry_date: string;
};
export type OrderItem = {
  id: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  quantity: number;
  unit_price: number;
  price_tier_id: string;
  price_tier_code: string;
  line_discount: number;
  line_total: number;
  allocated_quantity: number;
  on_hand: number;
  allocations: Allocation[];
};
export type Payment = {
  id: string;
  order_id: string;
  amount: number;
  method: PaymentMethod;
  provider: string | null;
  transaction_ref: string | null;
  status: PaymentRecordStatus;
  paid_at: string | null;
  recorded_by: string | null;
  created_at: string;
  updated_at: string;
};
export type DeliveryAgent = {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  address: string | null;
  vehicle_type: VehicleType | null;
  id_proof_path: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
  deleted_at: string | null;
};
export type Delivery = {
  id: string;
  order_id: string;
  agent_id: string | null;
  agent: DeliveryAgent | null;
  status: DeliveryStatus;
  assigned_at: string | null;
  dispatched_at: string | null;
  delivered_at: string | null;
  proof_path: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};
export type StatusHistory = {
  id: string;
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  note: string | null;
  changed_by: string | null;
  created_at: string;
};
export type OrderDetail = OrderSummary & {
  items: OrderItem[];
  history: StatusHistory[];
  payments: Payment[];
  delivery: Delivery | null;
  collected_total: number;
  balance_due: number;
  currency: string;
};
export type OrderList = {
  items: OrderSummary[];
  total: number;
  page: number;
  page_size: number;
  status_counts: Record<"ALL" | OrderStatus, number>;
};
export type OrderPayload = {
  customer_id: string;
  warehouse_id: string;
  items: Array<{ product_id: string; quantity: number; line_discount: number }>;
  discount_total: number;
  tax_total: number;
  delivery_address: string | null;
  delivery_location: string | null;
  notes: string | null;
};
export type OrderPreview = {
  customer_id: string;
  warehouse_id: string;
  price_tier_id: string;
  price_tier_code: string;
  items: OrderItem[];
  subtotal: number;
  discount_total: number;
  tax_total: number;
  total_amount: number;
  currency: string;
};

export const orderStatusLabels: Record<OrderStatus, string> = {
  PENDING: "Pending",
  APPROVED: "Approved",
  PENDING_DELIVERY: "Pending delivery",
  DELIVERED: "Delivered",
  FAILED: "Failed",
  UNFOUND: "Unfound",
  CANCELLED: "Cancelled",
};
export const paymentStatusLabels: Record<PaymentStatus, string> = {
  UNPAID: "Unpaid",
  PARTIAL: "Partial",
  PAID: "Paid",
};

// Phase 0 dashboard preview remains static until Phase 5 aggregate wiring.
export type PreviewOrder = {
  id: string;
  orderNumber: string;
  customer: string;
  location: string;
  total: number;
  status: OrderStatus;
};
export const previewOrders: PreviewOrder[] = [
  {
    id: "1",
    orderNumber: "KB-2026-000124",
    customer: "Upendo Community Pharmacy",
    location: "Kinondoni",
    total: 3845000,
    status: "PENDING",
  },
  {
    id: "2",
    orderNumber: "KB-2026-000123",
    customer: "AfyaPlus DLDM",
    location: "Mikocheni",
    total: 1284000,
    status: "APPROVED",
  },
  {
    id: "3",
    orderNumber: "KB-2026-000122",
    customer: "Mwanza Medical Stores",
    location: "Mwanza",
    total: 6720000,
    status: "PENDING_DELIVERY",
  },
  {
    id: "4",
    orderNumber: "KB-2026-000121",
    customer: "Jitegemee Pharmacy",
    location: "Arusha",
    total: 2190000,
    status: "DELIVERED",
  },
];
