import { apiBaseUrl } from "@/features/auth/auth-client";
import type {
  Brand,
  BrandPayload,
  CatalogImportResult,
  Category,
  CategoryPayload,
  CategoryTree,
  InventoryProduct,
  InventorySummary,
  ListResponse,
  PriceTier,
  Product,
  ProductBatch,
  ProductDetail,
  ProductImage,
  ProductPayload,
  RuntimeSettings,
  StockMovement,
  Warehouse,
  WarehousePayload,
} from "@/features/catalog/types";
import { apiClient } from "@/lib/api-client";

export type ProductFilters = {
  search?: string;
  category_id?: string;
  brand_id?: string;
  product_type?: string;
  is_active?: boolean;
  verification_status?: string;
  stock?: string;
  warehouse_id?: string;
};

const listParams = { page: 1, page_size: 100 };

export function uploadUrl(path: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  return `${apiBaseUrl.replace(/\/api\/v1\/?$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function listWarehouses(search = ""): Promise<ListResponse<Warehouse>> {
  const response = await apiClient.get<ListResponse<Warehouse>>("/warehouses", {
    params: { ...listParams, sort: "name:asc", search: search || undefined },
  });
  return response.data;
}
export async function saveWarehouse(payload: WarehousePayload, id?: string) {
  const response = id
    ? await apiClient.patch<Warehouse>(`/warehouses/${id}`, payload)
    : await apiClient.post<Warehouse>("/warehouses", payload);
  return response.data;
}
export async function deleteWarehouse(id: string) {
  await apiClient.delete(`/warehouses/${id}`);
}

export async function listCategories(search = ""): Promise<ListResponse<Category>> {
  const response = await apiClient.get<ListResponse<Category>>("/categories", {
    params: { ...listParams, sort: "sort_order:asc", search: search || undefined },
  });
  return response.data;
}
export async function getCategoryTree(): Promise<CategoryTree[]> {
  const response = await apiClient.get<CategoryTree[]>("/categories/tree");
  return response.data;
}
export async function saveCategory(payload: CategoryPayload, id?: string) {
  const response = id
    ? await apiClient.patch<Category>(`/categories/${id}`, payload)
    : await apiClient.post<Category>("/categories", payload);
  return response.data;
}
export async function reorderCategories(items: Array<{ id: string; sort_order: number }>) {
  const response = await apiClient.post<Category[]>("/categories/reorder", { items });
  return response.data;
}
export async function deleteCategory(id: string) {
  await apiClient.delete(`/categories/${id}`);
}

export async function listBrands(search = ""): Promise<ListResponse<Brand>> {
  const response = await apiClient.get<ListResponse<Brand>>("/brands", {
    params: { ...listParams, sort: "name:asc", search: search || undefined },
  });
  return response.data;
}
export async function saveBrand(payload: BrandPayload, id?: string) {
  const response = id
    ? await apiClient.patch<Brand>(`/brands/${id}`, payload)
    : await apiClient.post<Brand>("/brands", payload);
  return response.data;
}
export async function deleteBrand(id: string) {
  await apiClient.delete(`/brands/${id}`);
}

export async function listProducts(
  filters: ProductFilters = {},
): Promise<ListResponse<Product>> {
  const response = await apiClient.get<ListResponse<Product>>("/products", {
    params: { ...listParams, sort: "name:asc", ...filters },
  });
  return response.data;
}
export async function getProduct(id: string): Promise<ProductDetail> {
  const response = await apiClient.get<ProductDetail>(`/products/${id}`);
  return response.data;
}
export async function saveProduct(payload: ProductPayload, id?: string) {
  const response = id
    ? await apiClient.patch<ProductDetail>(`/products/${id}`, payload)
    : await apiClient.post<ProductDetail>("/products", payload);
  return response.data;
}
export async function deleteProduct(id: string) {
  await apiClient.delete(`/products/${id}`);
}
export async function verifyProduct(id: string) {
  const response = await apiClient.post(`/products/${id}/verify`);
  return response.data;
}
export async function saveProductPrices(
  productId: string,
  prices: Array<{
    price_tier_id: string;
    price: number;
    mrp: number | null;
    discount: number | null;
  }>,
) {
  const response = await apiClient.put(`/products/${productId}/prices`, { prices });
  return response.data;
}
export async function uploadProductImage(
  productId: string,
  file: File,
  isPrimary: boolean,
) {
  const body = new FormData();
  body.append("file", file);
  body.append("is_primary", String(isPrimary));
  body.append("sort_order", "0");
  const response = await apiClient.post<ProductImage>(
    `/products/${productId}/images`,
    body,
    {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 30_000,
    },
  );
  return response.data;
}
export async function updateProductImage(
  id: string,
  payload: Partial<Pick<ProductImage, "is_primary" | "sort_order">>,
) {
  const response = await apiClient.patch<ProductImage>(`/product-images/${id}`, payload);
  return response.data;
}
export async function deleteProductImage(id: string) {
  await apiClient.delete(`/product-images/${id}`);
}

export async function listPriceTiers(): Promise<ListResponse<PriceTier>> {
  const response = await apiClient.get<ListResponse<PriceTier>>("/price-tiers", {
    params: { ...listParams, is_active: true },
  });
  return response.data;
}
export async function getCatalogSettings(): Promise<RuntimeSettings> {
  const response = await apiClient.get<RuntimeSettings>("/settings/catalog");
  return response.data;
}

export async function listBatches(
  params: Record<string, string | undefined> = {},
): Promise<ListResponse<ProductBatch>> {
  const response = await apiClient.get<ListResponse<ProductBatch>>("/product-batches", {
    params: { ...listParams, sort: "expiry_date:asc", ...params },
  });
  return response.data;
}
export async function createBatch(payload: {
  product_id: string;
  warehouse_id: string;
  batch_number: string;
  expiry_date: string;
  quantity_available: number;
  cost_price: number | null;
  received_date: string;
  note: string | null;
}) {
  const response = await apiClient.post<ProductBatch>("/product-batches", payload);
  return response.data;
}
export async function updateBatch(
  id: string,
  payload: Partial<
    Pick<ProductBatch, "expiry_date" | "cost_price" | "received_date" | "status">
  >,
) {
  const response = await apiClient.patch<ProductBatch>(`/product-batches/${id}`, payload);
  return response.data;
}
export async function adjustBatch(id: string, delta: number, note: string) {
  const response = await apiClient.post<ProductBatch>(`/product-batches/${id}/adjust`, {
    delta,
    note,
  });
  return response.data;
}

export async function getInventorySummary(warehouseId?: string): Promise<InventorySummary> {
  const response = await apiClient.get<InventorySummary>("/inventory/summary", {
    params: { warehouse_id: warehouseId || undefined },
  });
  return response.data;
}
export async function listInventory(
  params: { search?: string; warehouse_id?: string; stock?: string } = {},
): Promise<ListResponse<InventoryProduct>> {
  const response = await apiClient.get<ListResponse<InventoryProduct>>("/inventory", {
    params: { ...listParams, ...params },
  });
  return response.data;
}
export async function listMovements(
  params: { product_id?: string; warehouse_id?: string; movement_type?: string } = {},
): Promise<ListResponse<StockMovement>> {
  const response = await apiClient.get<ListResponse<StockMovement>>(
    "/inventory/movements",
    {
      params: { ...listParams, ...params },
    },
  );
  return response.data;
}

export async function importCatalog(
  file: File,
  confirm: boolean,
): Promise<CatalogImportResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("confirm", String(confirm));
  const response = await apiClient.post<CatalogImportResult>("/catalog/import", body, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60_000,
  });
  return response.data;
}
export async function exportCatalog(): Promise<void> {
  const response = await apiClient.get<Blob>("/catalog/export", {
    responseType: "blob",
    timeout: 60_000,
  });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "kabisa-catalog.csv";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
