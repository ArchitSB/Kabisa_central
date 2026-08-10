import { useCallback, useMemo, useState } from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, Eye, Pencil, Plus, RotateCcw, Upload } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { BulkActionBar } from "@/components/ui/bulk-action-bar";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { FilterBar, FilterField, SearchInput } from "@/components/ui/filter-bar";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { DeleteRowAction, RowActions } from "@/components/ui/row-actions";
import { useHasPermission } from "@/features/auth/auth-store";
import {
  deleteProduct,
  listBrands,
  listCategories,
  listProducts,
  listWarehouses,
  saveProduct,
  uploadUrl,
  type ProductFilters,
} from "@/features/catalog/catalog-api";
import type { Product, ProductPayload } from "@/features/catalog/types";
import { CatalogImportDrawer } from "@/features/products/catalog-import-drawer";
import { ProductDrawer } from "@/features/products/product-drawer";
import { productTypeOptions } from "@/features/products/product-options";
import {
  PrescriptionBadge,
  ProductPlaceholder,
  ProductTypeBadge,
  StockBadge,
  VerificationBadge,
} from "@/features/products/product-ui";
import { getApiErrorDetail } from "@/lib/api-errors";
import { bulkResultMessage, downloadSection, runBulkAction } from "@/lib/data-controls";
import { useDebouncedValue } from "@/lib/use-debounced-value";

const emptyFilters = {
  category_id: "",
  brand_id: "",
  product_type: "",
  is_active: "",
  verification_status: "",
  stock: "",
  warehouse_id: "",
};
type Filters = typeof emptyFilters;

function payloadFor(product: Product, isActive = product.is_active): ProductPayload {
  return {
    name: product.name,
    sku: product.sku,
    description: product.description,
    category_id: product.category_id,
    brand_id: product.brand_id,
    product_type: product.product_type,
    requires_prescription: product.requires_prescription,
    registration_no: product.registration_no,
    generic_name: product.generic_name,
    strength: product.strength,
    pack_size: product.pack_size,
    unit: product.unit,
    hsn_code: product.hsn_code,
    base_mrp: product.base_mrp,
    low_stock_threshold: product.low_stock_threshold,
    is_active: isActive,
    is_featured: product.is_featured,
  };
}

export function ProductsPage() {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [selected, setSelected] = useState<Product[]>([]);
  const [deleting, setDeleting] = useState<Product | null>(null);
  const [bulkDelete, setBulkDelete] = useState(false);
  const deferredSearch = useDebouncedValue(search.trim());
  const canCreate = useHasPermission("products.create");
  const canEdit = useHasPermission("products.edit");
  const canDelete = useHasPermission("products.delete");
  const canVerify = useHasPermission("products.verify");
  const canImport = useHasPermission("catalog.import");
  const canExport = useHasPermission("catalog.export");
  const queryClient = useQueryClient();
  const params: ProductFilters = {
    search: deferredSearch || undefined,
    category_id: filters.category_id || undefined,
    brand_id: filters.brand_id || undefined,
    product_type: filters.product_type || undefined,
    is_active: filters.is_active === "" ? undefined : filters.is_active === "true",
    verification_status: filters.verification_status || undefined,
    stock: filters.stock || undefined,
    warehouse_id: filters.warehouse_id || undefined,
  };
  const products = useQuery({
    queryKey: ["products", params],
    queryFn: () => listProducts(params),
    placeholderData: keepPreviousData,
  });
  const categories = useQuery({
    queryKey: ["categories", "filters"],
    queryFn: () => listCategories(),
  });
  const brands = useQuery({ queryKey: ["brands", "filters"], queryFn: () => listBrands() });
  const warehouses = useQuery({
    queryKey: ["warehouses", "filters"],
    queryFn: () => listWarehouses(),
  });
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["products"] }),
      queryClient.invalidateQueries({ queryKey: ["inventory"] }),
    ]);
  const update = useMutation({
    mutationFn: ({ product, active }: { product: Product; active: boolean }) =>
      saveProduct(payloadFor(product, active), product.id),
    onSuccess: refresh,
    onError: (error) =>
      toast.error("Product status could not be changed", {
        description: getApiErrorDetail(error),
      }),
  });
  const remove = useMutation({
    mutationFn: async (items: Product[]) => {
      for (const item of items) await deleteProduct(item.id);
    },
    onSuccess: async () => {
      await refresh();
      setDeleting(null);
      setBulkDelete(false);
      setSelected([]);
      toast.success("Product removed");
    },
    onError: (error) =>
      toast.error("Product could not be removed", {
        description: getApiErrorDetail(error),
      }),
  });
  const bulk = useMutation({
    mutationFn: (action: string) =>
      runBulkAction("/products/bulk", {
        ids: selected.map((item) => item.id),
        action,
      }),
    onSuccess: async (result) => {
      await refresh();
      setSelected([]);
      setBulkDelete(false);
      const message = bulkResultMessage(result);
      if (result.skipped || result.failed)
        toast.warning(message.title, { description: message.description });
      else toast.success(message.title);
    },
    onError: (error) =>
      toast.error("Bulk action failed", { description: getApiErrorDetail(error) }),
  });
  const handleSelection = useCallback((rows: Product[]) => setSelected(rows), []);
  const columns = useMemo<ColumnDef<Product>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Product",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            {uploadUrl(row.original.primary_image) ? (
              <img
                src={uploadUrl(row.original.primary_image) ?? ""}
                alt=""
                className="size-11 rounded-control border border-border bg-surface object-contain p-1"
              />
            ) : (
              <ProductPlaceholder />
            )}
            <span>
              <Link
                to={`/products/${row.original.id}`}
                className="font-semibold text-foreground hover:text-primary-800 hover:underline"
              >
                {row.original.name}
              </Link>
              <span className="block max-w-[240px] truncate text-xs text-secondary">
                {[row.original.generic_name, row.original.strength]
                  .filter(Boolean)
                  .join(" · ") || "No generic name"}
              </span>
              {row.original.requires_prescription ? (
                <span className="mt-1 block">
                  <PrescriptionBadge />
                </span>
              ) : null}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "sku",
        header: "SKU",
        cell: ({ row }) => <span className="font-mono text-xs">{row.original.sku}</span>,
      },
      {
        accessorKey: "product_type",
        header: "Type",
        cell: ({ row }) => <ProductTypeBadge type={row.original.product_type} />,
      },
      { accessorFn: (item) => item.category.name, id: "category", header: "Category" },
      {
        accessorFn: (item) => item.brand?.name,
        id: "brand",
        header: "Brand",
        cell: ({ row }) => (
          <span className="text-secondary">{row.original.brand?.name ?? "—"}</span>
        ),
      },
      {
        accessorKey: "on_hand",
        header: "On-hand",
        cell: ({ row }) => (
          <StockBadge state={row.original.stock_status} onHand={row.original.on_hand} />
        ),
      },
      {
        accessorKey: "verification_status",
        header: "Verification",
        cell: ({ row }) => <VerificationBadge status={row.original.verification_status} />,
      },
      {
        accessorKey: "is_active",
        header: "Active",
        cell: ({ row }) =>
          canEdit ? (
            <button
              type="button"
              className="inline-flex min-h-10 min-w-11 items-center justify-center rounded-full"
              aria-label={`Set ${row.original.name} ${row.original.is_active ? "inactive" : "active"}`}
              onClick={() =>
                update.mutate({ product: row.original, active: !row.original.is_active })
              }
            >
              <span
                className={`inline-flex h-6 w-11 items-center rounded-full p-0.5 transition-colors ${row.original.is_active ? "bg-success" : "bg-neutral"}`}
              >
                <span
                  className={`size-5 rounded-full bg-white shadow-sm transition-transform ${row.original.is_active ? "translate-x-5" : "translate-x-0"}`}
                />
              </span>
            </button>
          ) : (
            <span>{row.original.is_active ? "Yes" : "No"}</span>
          ),
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        meta: { align: "right" },
        cell: ({ row }) => (
          <RowActions>
            <Button asChild variant="ghost" size="sm">
              <Link to={`/products/${row.original.id}`}>
                <Eye aria-hidden="true" />
                View
              </Link>
            </Button>
            {canEdit ? (
              <ProductDrawer
                product={row.original}
                trigger={
                  <Button variant="ghost" size="sm">
                    <Pencil aria-hidden="true" />
                    Edit
                  </Button>
                }
              />
            ) : null}
            {canDelete ? (
              <DeleteRowAction
                label={`Delete ${row.original.name}`}
                onClick={() => setDeleting(row.original)}
              />
            ) : null}
          </RowActions>
        ),
      },
    ],
    [canDelete, canEdit, update],
  );
  async function doExport() {
    try {
      await downloadSection("/products/export", { ...params }, "kabisa-products.xlsx");
      toast.success("Products downloaded");
    } catch (error) {
      toast.error("Catalog could not be exported", {
        description: getApiErrorDetail(error),
      });
    }
  }
  function bulkAction(action: string) {
    if (action === "delete") setBulkDelete(true);
    else if (action === "export") {
      void downloadSection(
        "/products/export",
        { ids: selected.map((item) => item.id) },
        "kabisa-selected-products.xlsx",
      ).catch((error) =>
        toast.error("Products could not be downloaded", {
          description: getApiErrorDetail(error),
        }),
      );
    } else bulk.mutate(action);
  }
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Catalog"
        title="Products"
        subtitle="Manage classification, pricing, verification, imagery, and warehouse-aware availability."
        actions={
          <>
            {canImport ? (
              <CatalogImportDrawer
                trigger={
                  <Button variant="secondary">
                    <Upload aria-hidden="true" />
                    Import CSV
                  </Button>
                }
              />
            ) : null}
            {canExport ? (
              <Button variant="secondary" onClick={doExport}>
                <Download aria-hidden="true" />
                Download
              </Button>
            ) : null}
            {canCreate ? (
              <ProductDrawer
                trigger={
                  <Button>
                    <Plus aria-hidden="true" />
                    Add product
                  </Button>
                }
              />
            ) : null}
          </>
        }
      />
      <FilterBar>
        <FilterField label="Search" htmlFor="product-search">
          <SearchInput
            id="product-search"
            value={search}
            onValueChange={setSearch}
            placeholder="Name, SKU, generic"
          />
        </FilterField>
        <FilterField label="Category" htmlFor="product-category-filter">
          <select
            id="product-category-filter"
            className="control-base w-full"
            value={filters.category_id}
            onChange={(event) =>
              setFilters((current) => ({ ...current, category_id: event.target.value }))
            }
          >
            <option value="">All categories</option>
            {categories.data?.items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Brand" htmlFor="product-brand-filter">
          <select
            id="product-brand-filter"
            className="control-base w-full"
            value={filters.brand_id}
            onChange={(event) =>
              setFilters((current) => ({ ...current, brand_id: event.target.value }))
            }
          >
            <option value="">All brands</option>
            {brands.data?.items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Type" htmlFor="product-type-filter">
          <select
            id="product-type-filter"
            className="control-base w-full"
            value={filters.product_type}
            onChange={(event) =>
              setFilters((current) => ({ ...current, product_type: event.target.value }))
            }
          >
            <option value="">All types</option>
            {productTypeOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Stock" htmlFor="product-stock-filter">
          <select
            id="product-stock-filter"
            className="control-base w-full"
            value={filters.stock}
            onChange={(event) =>
              setFilters((current) => ({ ...current, stock: event.target.value }))
            }
          >
            <option value="">All stock</option>
            <option value="in">In stock</option>
            <option value="low">Low stock</option>
            <option value="out">Out of stock</option>
          </select>
        </FilterField>
        <FilterField label="Warehouse" htmlFor="product-warehouse-filter">
          <select
            id="product-warehouse-filter"
            className="control-base w-full"
            value={filters.warehouse_id}
            onChange={(event) =>
              setFilters((current) => ({ ...current, warehouse_id: event.target.value }))
            }
          >
            <option value="">All warehouses</option>
            {warehouses.data?.items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Verification" htmlFor="product-verification-filter">
          <select
            id="product-verification-filter"
            className="control-base w-full"
            value={filters.verification_status}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                verification_status: event.target.value,
              }))
            }
          >
            <option value="">All verification</option>
            <option value="VERIFIED">Verified</option>
            <option value="UNVERIFIED">Unverified</option>
          </select>
        </FilterField>
        <FilterField label="Status" htmlFor="product-active-filter">
          <select
            id="product-active-filter"
            className="control-base w-full"
            value={filters.is_active}
            onChange={(event) =>
              setFilters((current) => ({ ...current, is_active: event.target.value }))
            }
          >
            <option value="">All statuses</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </FilterField>
        <Button
          variant="ghost"
          className="w-full xl:w-auto"
          onClick={() => {
            setSearch("");
            setFilters(emptyFilters);
          }}
        >
          <RotateCcw aria-hidden="true" />
          Reset
        </Button>
      </FilterBar>
      {canEdit || canDelete || canVerify || canExport ? (
        <BulkActionBar
          selectedCount={selected.length}
          totalCount={products.data?.total ?? 0}
          actions={[
            ...(canEdit
              ? [
                  { value: "activate", label: "Activate products" },
                  { value: "deactivate", label: "Deactivate products" },
                  { value: "feature", label: "Feature products" },
                  { value: "unfeature", label: "Unfeature products" },
                ]
              : []),
            ...(canVerify ? [{ value: "verify", label: "Verify products" }] : []),
            ...(canDelete ? [{ value: "delete", label: "Delete products" }] : []),
            ...(canExport ? [{ value: "export", label: "Export selected" }] : []),
          ]}
          onAction={bulkAction}
          pending={bulk.isPending || remove.isPending}
          noun="products"
        />
      ) : null}
      {products.isPending ? (
        <LoadingState label="Loading products…" />
      ) : products.isError ? (
        <ErrorState
          title="Products could not be loaded"
          onRetry={() => products.refetch()}
        />
      ) : (
        <DataTable
          ariaLabel="Products"
          columns={columns}
          data={products.data.items}
          getRowId={(item) => item.id}
          onSelectionChange={handleSelection}
          selectable={canEdit || canDelete || canVerify || canExport}
          pageSize={12}
        />
      )}
      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove product?"
        description={`This soft-deletes ${deleting?.name ?? "the product"}. Products with on-hand stock or open orders are protected.`}
        confirmLabel="Remove product"
        destructive
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate([deleting])}
      />
      <ConfirmDialog
        open={bulkDelete}
        onOpenChange={setBulkDelete}
        title={`Remove ${selected.length} products?`}
        description="Products with on-hand stock or open orders are skipped; eligible products are soft-deleted."
        confirmLabel="Remove selected"
        destructive
        pending={bulk.isPending}
        onConfirm={() => bulk.mutate("delete")}
      />
    </div>
  );
}
