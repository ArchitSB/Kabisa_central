import type { ListResponse } from "@/features/catalog/types";
import type {
  DeliveryAgent,
  OrderDetail,
  OrderList,
  OrderPayload,
  OrderPreview,
  OrderStatus,
  PaymentMethod,
  PaymentRecordStatus,
  PaymentStatus,
  VehicleType,
} from "@/features/orders/orders.data";
import { apiClient } from "@/lib/api-client";

export type OrderFilters = {
  search?: string;
  order_status?: OrderStatus;
  payment_status?: PaymentStatus;
  warehouse_id?: string;
  date_from?: string;
  date_to?: string;
};

export async function listOrders(filters: OrderFilters = {}) {
  const response = await apiClient.get<OrderList>("/orders", {
    params: { page: 1, page_size: 100, sort: "created_at:desc", ...filters },
  });
  return response.data;
}
export async function getOrder(id: string) {
  const response = await apiClient.get<OrderDetail>(`/orders/${id}`);
  return response.data;
}
export async function previewOrder(payload: OrderPayload) {
  const response = await apiClient.post<OrderPreview>("/orders/preview", payload);
  return response.data;
}
export async function createOrder(payload: OrderPayload) {
  const response = await apiClient.post<OrderDetail>("/orders", payload);
  return response.data;
}
export async function deleteOrder(id: string) {
  await apiClient.delete(`/orders/${id}`);
}
export async function approveOrder(id: string, note: string | null = null) {
  const response = await apiClient.post<OrderDetail>(`/orders/${id}/approve`, { note });
  return response.data;
}
export async function setOrderStatus(
  id: string,
  status: Extract<OrderStatus, "FAILED" | "UNFOUND" | "CANCELLED">,
  note: string | null,
) {
  const path = status === "CANCELLED" ? "cancel" : status.toLowerCase();
  const response = await apiClient.post<OrderDetail>(`/orders/${id}/${path}`, { note });
  return response.data;
}
export async function bulkOrderStatus(ids: string[], status: OrderStatus) {
  const response = await apiClient.post<{
    updated: string[];
    failed: Record<string, string>;
  }>("/orders/bulk-status", { order_ids: ids, status });
  return response.data;
}
export async function recordPayment(
  orderId: string,
  payload: {
    amount: number;
    method: PaymentMethod;
    provider: string | null;
    transaction_ref: string | null;
    status: PaymentRecordStatus;
  },
) {
  const response = await apiClient.post(`/orders/${orderId}/payments`, payload);
  return response.data;
}
export async function assignDelivery(
  orderId: string,
  agentId: string,
  notes: string | null,
) {
  const response = await apiClient.post<OrderDetail>(`/orders/${orderId}/delivery`, {
    agent_id: agentId,
    notes,
  });
  return response.data;
}
export async function dispatchDelivery(orderId: string) {
  const response = await apiClient.post<OrderDetail>(
    `/orders/${orderId}/delivery/dispatch`,
  );
  return response.data;
}
export async function completeDelivery(orderId: string, proof: File, notes: string) {
  const body = new FormData();
  body.append("proof", proof);
  if (notes) body.append("notes", notes);
  const response = await apiClient.post<OrderDetail>(
    `/orders/${orderId}/delivery/deliver`,
    body,
    { headers: { "Content-Type": "multipart/form-data" }, timeout: 30_000 },
  );
  return response.data;
}
export async function downloadDeliveryProof(deliveryId: string) {
  const response = await apiClient.get<Blob>(`/deliveries/${deliveryId}/proof`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  window.open(url, "_blank", "noopener,noreferrer");
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}
export async function listDeliveryAgents(
  filters: {
    search?: string;
    is_active?: boolean;
    vehicle_type?: VehicleType;
  } = {},
) {
  const response = await apiClient.get<ListResponse<DeliveryAgent>>("/delivery-agents", {
    params: { page: 1, page_size: 100, ...filters },
  });
  return response.data;
}
export async function saveDeliveryAgent(
  payload: Omit<
    DeliveryAgent,
    | "id"
    | "id_proof_path"
    | "created_at"
    | "updated_at"
    | "created_by"
    | "updated_by"
    | "deleted_at"
  >,
  id?: string,
) {
  const response = id
    ? await apiClient.patch<DeliveryAgent>(`/delivery-agents/${id}`, payload)
    : await apiClient.post<DeliveryAgent>("/delivery-agents", payload);
  return response.data;
}
export async function deleteDeliveryAgent(id: string) {
  await apiClient.delete(`/delivery-agents/${id}`);
}
export async function uploadDeliveryAgentProof(id: string, file: File) {
  const body = new FormData();
  body.append("file", file);
  const response = await apiClient.post<DeliveryAgent>(
    `/delivery-agents/${id}/id-proof`,
    body,
    { headers: { "Content-Type": "multipart/form-data" }, timeout: 30_000 },
  );
  return response.data;
}
