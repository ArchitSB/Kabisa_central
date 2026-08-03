import type { ListResponse } from "@/features/catalog/types";
import type { Coupon, CouponPayload, CouponValidation } from "@/features/coupons/types";
import { apiClient } from "@/lib/api-client";

export async function listCoupons(filters: { search?: string; is_active?: boolean } = {}) {
  const response = await apiClient.get<ListResponse<Coupon>>("/coupons", {
    params: { page: 1, page_size: 100, sort: "created_at:desc", ...filters },
  });
  return response.data;
}
export async function saveCoupon(payload: CouponPayload, id?: string) {
  const response = id
    ? await apiClient.patch<Coupon>(`/coupons/${id}`, payload)
    : await apiClient.post<Coupon>("/coupons", payload);
  return response.data;
}
export async function deleteCoupon(id: string) {
  await apiClient.delete(`/coupons/${id}`);
}
export async function validateCoupon(code: string, subtotal: number) {
  const response = await apiClient.post<CouponValidation>("/coupons/validate", {
    code,
    subtotal,
  });
  return response.data;
}
