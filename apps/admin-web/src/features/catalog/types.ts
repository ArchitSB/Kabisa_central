export type ListResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type ProductType =
  "PRESCRIPTION" | "OTC" | "SPECIALTY" | "NUTRACEUTICAL" | "MEDICAL_DEVICE" | "CONSUMABLE";
export type ProductUnit = "PCS" | "BOX" | "STRIP" | "BOTTLE" | "PACK" | "VIAL" | "TUBE";
export type VerificationStatus = "UNVERIFIED" | "VERIFIED";
export type BatchStatus = "ACTIVE" | "DEPLETED" | "EXPIRED" | "QUARANTINED";
export type MovementType =
  "INBOUND" | "OUTBOUND" | "ADJUSTMENT" | "RETURN" | "TRANSFER" | "INITIAL";
export type StockState = "in" | "low" | "out";

type AuditFields = {
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
};

export type Warehouse = AuditFields & {
  id: string;
  name: string;
  code: string;
  address: string;
  region: string;
  is_primary: boolean;
  is_active: boolean;
  deleted_at: string | null;
};

export type WarehousePayload = Omit<Warehouse, keyof AuditFields | "id" | "deleted_at">;

export type CategorySummary = { id: string; name: string; slug: string };
export type Category = AuditFields & {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
  parent: CategorySummary | null;
  image_path: string | null;
  description: string | null;
  is_active: boolean;
  sort_order: number;
  deleted_at: string | null;
};
export type CategoryTree = Category & { children: CategoryTree[] };
export type CategoryPayload = Pick<
  Category,
  "name" | "parent_id" | "image_path" | "description" | "is_active" | "sort_order"
>;

export type BrandSummary = { id: string; name: string; slug: string };
export type Brand = AuditFields & {
  id: string;
  name: string;
  slug: string;
  logo_path: string | null;
  is_active: boolean;
  deleted_at: string | null;
};
export type BrandPayload = Pick<Brand, "name" | "logo_path" | "is_active">;

export type PriceTier = AuditFields & {
  id: string;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
};

export type ProductImage = AuditFields & {
  id: string;
  product_id: string;
  file_path: string;
  is_primary: boolean;
  sort_order: number;
};

export type ProductPrice = AuditFields & {
  id: string;
  product_id: string;
  price_tier: PriceTier;
  price: number;
  mrp: number | null;
  discount: number | null;
};

export type WarehouseStock = {
  warehouse_id: string;
  warehouse_name: string;
  warehouse_code: string;
  on_hand: number;
};

export type ProductBatch = AuditFields & {
  id: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  warehouse_id: string;
  warehouse_name: string;
  warehouse_code: string;
  batch_number: string;
  expiry_date: string;
  quantity_available: number;
  quantity_reserved: number;
  on_hand: number;
  cost_price: number | null;
  received_date: string;
  status: BatchStatus;
  is_expired: boolean;
  is_expiring_soon: boolean;
  deleted_at: string | null;
};

export type Product = AuditFields & {
  id: string;
  name: string;
  slug: string;
  sku: string;
  description: string | null;
  category_id: string;
  category: CategorySummary;
  brand_id: string | null;
  brand: BrandSummary | null;
  product_type: ProductType;
  requires_prescription: boolean;
  registration_no: string | null;
  generic_name: string | null;
  strength: string | null;
  pack_size: string | null;
  unit: ProductUnit;
  hsn_code: string | null;
  base_mrp: number | null;
  low_stock_threshold: number | null;
  is_active: boolean;
  is_featured: boolean;
  verification_status: VerificationStatus;
  verified_by: string | null;
  verified_at: string | null;
  deleted_at: string | null;
  on_hand: number;
  stock_status: StockState;
  primary_image: string | null;
};

export type ProductDetail = Product & {
  images: ProductImage[];
  prices: ProductPrice[];
  warehouse_stock: WarehouseStock[];
  batches: Array<
    Omit<
      ProductBatch,
      | "product_id"
      | "product_name"
      | "product_sku"
      | "received_date"
      | "created_at"
      | "updated_at"
      | "created_by"
      | "updated_by"
      | "deleted_at"
    >
  >;
};

export type ProductPayload = Pick<
  Product,
  | "name"
  | "sku"
  | "description"
  | "category_id"
  | "brand_id"
  | "product_type"
  | "requires_prescription"
  | "registration_no"
  | "generic_name"
  | "strength"
  | "pack_size"
  | "unit"
  | "hsn_code"
  | "base_mrp"
  | "low_stock_threshold"
  | "is_active"
  | "is_featured"
>;

export type RuntimeSettings = {
  currency: string;
  expiring_soon_days: number;
  low_stock_default: number;
  stock_valuation: string;
};

export type InventoryBatch = Omit<
  ProductBatch,
  | "product_id"
  | "product_name"
  | "product_sku"
  | "received_date"
  | keyof AuditFields
  | "deleted_at"
>;
export type InventoryProduct = {
  product_id: string;
  name: string;
  sku: string;
  primary_image: string | null;
  low_stock_threshold: number;
  on_hand: number;
  stock_status: StockState;
  warehouse_stock: WarehouseStock[];
  batches: InventoryBatch[];
};
export type InventorySummary = {
  currency: string;
  total_items: number;
  stock_value: number;
  low_stock_count: number;
  out_of_stock_count: number;
  expiring_soon_count: number;
  cost_missing_batches: number;
};

export type StockMovement = {
  id: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  batch_id: string | null;
  batch_number: string | null;
  warehouse_id: string;
  warehouse_name: string;
  warehouse_code: string;
  movement_type: MovementType;
  quantity: number;
  reference_type: string;
  reference_id: string | null;
  note: string | null;
  created_by: string | null;
  created_at: string;
};

export type CatalogImportResult = {
  valid: boolean;
  committed: boolean;
  total_rows: number;
  valid_rows: number;
  created: number;
  updated: number;
  preview: Array<{ row: number; sku: string; name: string; action: string }>;
  errors: Array<{ row: number; field: string; detail: string }>;
};
