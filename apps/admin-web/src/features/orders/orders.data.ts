export type OrderStatus =
  | "PENDING"
  | "APPROVED"
  | "PENDING_DELIVERY"
  | "DELIVERED"
  | "FAILED"
  | "UNFOUND"
  | "CANCELLED";

export type PaymentStatus = "UNPAID" | "PARTIAL" | "PAID";

export type PreviewOrder = {
  id: string;
  orderNumber: string;
  customer: string;
  location: string;
  paymentStatus: PaymentStatus;
  total: number;
  items: number;
  createdAt: string;
  status: OrderStatus;
};

export const previewOrders: PreviewOrder[] = [
  {
    id: "1",
    orderNumber: "KB-2026-000124",
    customer: "Upendo Community Pharmacy",
    location: "Kinondoni, Dar es Salaam",
    paymentStatus: "PARTIAL",
    total: 3845000,
    items: 8,
    createdAt: "2026-07-26T08:42:00Z",
    status: "PENDING",
  },
  {
    id: "2",
    orderNumber: "KB-2026-000123",
    customer: "AfyaPlus DLDM",
    location: "Mikocheni, Dar es Salaam",
    paymentStatus: "PAID",
    total: 1284000,
    items: 4,
    createdAt: "2026-07-26T07:18:00Z",
    status: "APPROVED",
  },
  {
    id: "3",
    orderNumber: "KB-2026-000122",
    customer: "Mwanza Medical Stores",
    location: "Nyamagana, Mwanza",
    paymentStatus: "UNPAID",
    total: 6720000,
    items: 12,
    createdAt: "2026-07-25T15:36:00Z",
    status: "PENDING_DELIVERY",
  },
  {
    id: "4",
    orderNumber: "KB-2026-000121",
    customer: "Jitegemee Pharmacy",
    location: "Arusha City, Arusha",
    paymentStatus: "PAID",
    total: 2190000,
    items: 6,
    createdAt: "2026-07-25T11:20:00Z",
    status: "DELIVERED",
  },
  {
    id: "5",
    orderNumber: "KB-2026-000120",
    customer: "Tumaini Health Centre",
    location: "Dodoma City, Dodoma",
    paymentStatus: "UNPAID",
    total: 945000,
    items: 3,
    createdAt: "2026-07-24T16:05:00Z",
    status: "UNFOUND",
  },
  {
    id: "6",
    orderNumber: "KB-2026-000119",
    customer: "Baraka Pharmacy",
    location: "Temeke, Dar es Salaam",
    paymentStatus: "PARTIAL",
    total: 1580000,
    items: 5,
    createdAt: "2026-07-24T09:54:00Z",
    status: "FAILED",
  },
  {
    id: "7",
    orderNumber: "KB-2026-000118",
    customer: "Kilimanjaro Wholesale",
    location: "Moshi Urban, Kilimanjaro",
    paymentStatus: "UNPAID",
    total: 8420000,
    items: 18,
    createdAt: "2026-07-23T14:11:00Z",
    status: "CANCELLED",
  },
  {
    id: "8",
    orderNumber: "KB-2026-000117",
    customer: "Mlimani Community Pharmacy",
    location: "Ubungo, Dar es Salaam",
    paymentStatus: "PAID",
    total: 3365000,
    items: 9,
    createdAt: "2026-07-23T08:33:00Z",
    status: "DELIVERED",
  },
  {
    id: "9",
    orderNumber: "KB-2026-000116",
    customer: "Pamoja DLDM",
    location: "Morogoro Municipal",
    paymentStatus: "UNPAID",
    total: 785000,
    items: 2,
    createdAt: "2026-07-22T13:47:00Z",
    status: "APPROVED",
  },
];

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
