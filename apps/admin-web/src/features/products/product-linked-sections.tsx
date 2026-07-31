import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, PackagePlus, Star, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { FileUpload } from "@/components/ui/file-upload";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { useHasPermission } from "@/features/auth/auth-store";
import {
  createBatch,
  deleteProductImage,
  listPriceTiers,
  listWarehouses,
  saveProductPrices,
  updateProductImage,
  uploadProductImage,
  uploadUrl,
} from "@/features/catalog/catalog-api";
import type { ProductDetail } from "@/features/catalog/types";
import { getApiErrorDetail } from "@/lib/api-errors";
import { formatMoney } from "@/lib/utils";

const batchSchema = z.object({
  warehouse_id: z.string().uuid("Select a warehouse."),
  batch_number: z.string().trim().min(1, "Enter a batch number."),
  expiry_date: z.string().min(1, "Select an expiry date."),
  quantity_available: z.coerce.number().int().positive("Enter a positive quantity."),
  cost_price: z.string(),
  received_date: z.string().min(1),
  note: z.string(),
});
type BatchValues = z.infer<typeof batchSchema>;

export function ProductLinkedSections({
  product,
  currency,
}: {
  product: ProductDetail;
  currency: string;
}) {
  const [image, setImage] = useState<File | null>(null);
  const [prices, setPrices] = useState<Record<string, string>>({});
  const canEdit = useHasPermission("products.edit");
  const canPrice = useHasPermission("product_prices.manage");
  const canBatch = useHasPermission("batches.create");
  const queryClient = useQueryClient();
  const tiers = useQuery({ queryKey: ["price-tiers"], queryFn: listPriceTiers });
  const warehouses = useQuery({
    queryKey: ["warehouses", "options"],
    queryFn: () => listWarehouses(),
  });
  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ["product", product.id] });
  const imageMutation = useMutation({
    mutationFn: (file: File) =>
      uploadProductImage(product.id, file, product.images.length === 0),
    onSuccess: async () => {
      await refresh();
      setImage(null);
      toast.success("Product image uploaded");
    },
    onError: (error) =>
      toast.error("Image could not be uploaded", { description: getApiErrorDetail(error) }),
  });
  const imageUpdate = useMutation({
    mutationFn: ({ id, primary }: { id: string; primary: boolean }) =>
      updateProductImage(id, { is_primary: primary }),
    onSuccess: refresh,
    onError: (error) =>
      toast.error("Image could not be updated", { description: getApiErrorDetail(error) }),
  });
  const imageDelete = useMutation({
    mutationFn: deleteProductImage,
    onSuccess: refresh,
    onError: (error) =>
      toast.error("Image could not be removed", { description: getApiErrorDetail(error) }),
  });
  const priceMutation = useMutation({
    mutationFn: () =>
      saveProductPrices(
        product.id,
        (tiers.data?.items ?? []).map((tier) => ({
          price_tier_id: tier.id,
          price: Number(prices[tier.id] || 0),
          mrp: product.base_mrp,
          discount: null,
        })),
      ),
    onSuccess: async () => {
      await refresh();
      toast.success("Price matrix updated");
    },
    onError: (error) =>
      toast.error("Prices could not be updated", { description: getApiErrorDetail(error) }),
  });
  const batchForm = useForm<BatchValues>({
    resolver: zodResolver(batchSchema),
    defaultValues: {
      warehouse_id: "",
      batch_number: "",
      expiry_date: "",
      quantity_available: 1,
      cost_price: "",
      received_date: new Date().toISOString().slice(0, 10),
      note: "",
    },
  });
  const batchMutation = useMutation({
    mutationFn: (values: BatchValues) =>
      createBatch({
        product_id: product.id,
        warehouse_id: values.warehouse_id,
        batch_number: values.batch_number,
        expiry_date: values.expiry_date,
        quantity_available: values.quantity_available,
        cost_price: values.cost_price ? Number(values.cost_price) : null,
        received_date: values.received_date,
        note: values.note || null,
      }),
    onSuccess: async () => {
      await Promise.all([
        refresh(),
        queryClient.invalidateQueries({ queryKey: ["inventory"] }),
      ]);
      batchForm.reset({
        warehouse_id: "",
        batch_number: "",
        expiry_date: "",
        quantity_available: 1,
        cost_price: "",
        received_date: new Date().toISOString().slice(0, 10),
        note: "",
      });
      toast.success("Inbound batch recorded");
    },
    onError: (error) =>
      toast.error("Batch could not be recorded", { description: getApiErrorDetail(error) }),
  });

  useEffect(() => {
    setPrices(
      Object.fromEntries(
        product.prices.map((price) => [price.price_tier.id, String(price.price)]),
      ),
    );
  }, [product.prices]);

  return (
    <div className="space-y-8 border-t border-border px-6 py-6">
      <section aria-labelledby="product-images-heading">
        <div className="mb-4 flex items-center gap-2">
          <ImagePlus aria-hidden="true" className="size-4 text-primary-700" />
          <h3 id="product-images-heading" className="font-semibold">
            Images
          </h3>
        </div>
        {product.images.length ? (
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {product.images.map((item) => (
              <div
                key={item.id}
                className="relative overflow-hidden rounded-control border border-border bg-[#FBFCFB] p-2"
              >
                <img
                  src={uploadUrl(item.file_path) ?? ""}
                  alt=""
                  className="aspect-square w-full rounded-lg object-contain"
                />
                <div className="mt-2 flex items-center justify-between">
                  <button
                    type="button"
                    disabled={!canEdit || item.is_primary}
                    className="rounded-md p-1 text-secondary hover:bg-primary-50 hover:text-primary-800 disabled:text-primary-700"
                    aria-label={item.is_primary ? "Primary image" : "Set as primary image"}
                    onClick={() => imageUpdate.mutate({ id: item.id, primary: true })}
                  >
                    <Star
                      aria-hidden="true"
                      className="size-4"
                      fill={item.is_primary ? "currentColor" : "none"}
                    />
                  </button>
                  {canEdit ? (
                    <button
                      type="button"
                      className="rounded-md p-1 text-secondary hover:bg-danger-surface hover:text-danger"
                      aria-label="Delete image"
                      onClick={() => imageDelete.mutate(item.id)}
                    >
                      <Trash2 aria-hidden="true" className="size-4" />
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mb-4 text-sm text-secondary">No product images uploaded.</p>
        )}
        {canEdit ? (
          <>
            <FileUpload
              accept="image/jpeg,image/png,image/webp"
              file={image}
              onFileChange={setImage}
              label="Choose JPEG, PNG, or WebP"
              hint="Up to 5 MB. The first image becomes primary."
            />
            <Button
              type="button"
              variant="secondary"
              className="mt-3"
              disabled={!image || imageMutation.isPending}
              onClick={() => image && imageMutation.mutate(image)}
            >
              {imageMutation.isPending ? "Uploading…" : "Upload image"}
            </Button>
          </>
        ) : null}
      </section>
      <section aria-labelledby="product-prices-heading">
        <h3 id="product-prices-heading" className="font-semibold">
          Price matrix
        </h3>
        <p className="mt-1 text-xs text-secondary">
          All active tiers are saved atomically. Values display in {currency}.
        </p>
        <div className="mt-4 space-y-3">
          {tiers.data?.items.map((tier) => (
            <label
              key={tier.id}
              className="grid grid-cols-[minmax(120px,1fr)_minmax(140px,180px)] items-center gap-3 rounded-control border border-border p-3"
            >
              <span>
                <span className="block text-sm font-semibold">{tier.name}</span>
                <span className="text-xs text-secondary">{tier.code}</span>
              </span>
              <Input
                type="number"
                min={0}
                step="0.01"
                aria-label={`${tier.name} price`}
                disabled={!canPrice}
                value={prices[tier.id] ?? ""}
                onChange={(event) =>
                  setPrices((current) => ({ ...current, [tier.id]: event.target.value }))
                }
              />
            </label>
          ))}
        </div>
        {canPrice ? (
          <Button
            type="button"
            variant="secondary"
            className="mt-3"
            disabled={priceMutation.isPending || !tiers.data?.items.length}
            onClick={() => priceMutation.mutate()}
          >
            {priceMutation.isPending ? "Saving prices…" : "Save price matrix"}
          </Button>
        ) : null}
        {product.prices.length ? (
          <p className="mt-3 text-xs text-secondary">
            Current range:{" "}
            {formatMoney(
              Math.min(...product.prices.map((price) => Number(price.price))),
              currency,
            )}
            –
            {formatMoney(
              Math.max(...product.prices.map((price) => Number(price.price))),
              currency,
            )}
          </p>
        ) : null}
      </section>
      <section aria-labelledby="product-batches-heading">
        <div className="mb-1 flex items-center gap-2">
          <PackagePlus aria-hidden="true" className="size-4 text-primary-700" />
          <h3 id="product-batches-heading" className="font-semibold">
            Add inbound batch
          </h3>
        </div>
        <p className="text-xs text-secondary">
          Every receipt creates a warehouse-scoped stock movement.
        </p>
        {canBatch ? (
          <form
            className="mt-4 grid gap-4 sm:grid-cols-2"
            onSubmit={batchForm.handleSubmit((values) => batchMutation.mutate(values))}
          >
            <FormField
              label="Warehouse"
              htmlFor="batch-warehouse"
              error={batchForm.formState.errors.warehouse_id?.message}
            >
              <select
                id="batch-warehouse"
                className="control-base w-full"
                {...batchForm.register("warehouse_id")}
              >
                <option value="">Select location</option>
                {warehouses.data?.items
                  .filter((item) => item.is_active)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
              </select>
            </FormField>
            <FormField
              label="Batch number"
              htmlFor="batch-number"
              error={batchForm.formState.errors.batch_number?.message}
            >
              <Input id="batch-number" {...batchForm.register("batch_number")} />
            </FormField>
            <FormField
              label="Expiry"
              htmlFor="batch-expiry"
              error={batchForm.formState.errors.expiry_date?.message}
            >
              <Input id="batch-expiry" type="date" {...batchForm.register("expiry_date")} />
            </FormField>
            <FormField label="Received" htmlFor="batch-received">
              <Input
                id="batch-received"
                type="date"
                {...batchForm.register("received_date")}
              />
            </FormField>
            <FormField
              label="Quantity"
              htmlFor="batch-quantity"
              error={batchForm.formState.errors.quantity_available?.message}
            >
              <Input
                id="batch-quantity"
                type="number"
                min={1}
                {...batchForm.register("quantity_available")}
              />
            </FormField>
            <FormField label={`Unit cost (${currency})`} htmlFor="batch-cost">
              <Input
                id="batch-cost"
                type="number"
                min={0}
                step="0.01"
                {...batchForm.register("cost_price")}
              />
            </FormField>
            <FormField
              label="Receiving note"
              htmlFor="batch-note"
              className="sm:col-span-2"
            >
              <Input id="batch-note" {...batchForm.register("note")} />
            </FormField>
            <Button
              type="submit"
              variant="secondary"
              className="sm:col-span-2"
              disabled={batchMutation.isPending}
            >
              {batchMutation.isPending ? "Recording…" : "Record inbound batch"}
            </Button>
          </form>
        ) : null}
      </section>
    </div>
  );
}
