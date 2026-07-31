import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import {
  getCatalogSettings,
  getProduct,
  listBrands,
  listCategories,
  saveProduct,
} from "@/features/catalog/catalog-api";
import type {
  Product,
  ProductPayload,
  ProductType,
  ProductUnit,
} from "@/features/catalog/types";
import { ProductLinkedSections } from "@/features/products/product-linked-sections";
import { productTypeOptions } from "@/features/products/product-options";
import { getApiErrorDetail } from "@/lib/api-errors";

const units: ProductUnit[] = ["PCS", "BOX", "STRIP", "BOTTLE", "PACK", "VIAL", "TUBE"];
const schema = z.object({
  name: z.string().trim().min(2, "Enter a product name."),
  sku: z.string().trim().min(2, "Enter a SKU."),
  description: z.string().max(5000),
  category_id: z.string().uuid("Select a category."),
  brand_id: z.string(),
  product_type: z.enum([
    "PRESCRIPTION",
    "OTC",
    "SPECIALTY",
    "NUTRACEUTICAL",
    "MEDICAL_DEVICE",
    "CONSUMABLE",
  ]),
  requires_prescription: z.boolean(),
  registration_no: z.string(),
  generic_name: z.string(),
  strength: z.string(),
  pack_size: z.string(),
  unit: z.enum(["PCS", "BOX", "STRIP", "BOTTLE", "PACK", "VIAL", "TUBE"]),
  hsn_code: z.string(),
  base_mrp: z.string(),
  low_stock_threshold: z.string(),
  is_active: z.boolean(),
  is_featured: z.boolean(),
});
type Values = z.infer<typeof schema>;

const blankValues: Values = {
  name: "",
  sku: "",
  description: "",
  category_id: "",
  brand_id: "",
  product_type: "OTC",
  requires_prescription: false,
  registration_no: "",
  generic_name: "",
  strength: "",
  pack_size: "",
  unit: "PCS",
  hsn_code: "",
  base_mrp: "",
  low_stock_threshold: "",
  is_active: true,
  is_featured: false,
};

export function ProductDrawer({
  trigger,
  product,
}: {
  trigger: React.ReactNode;
  product?: Product;
}) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const categories = useQuery({
    queryKey: ["categories", "product-options"],
    queryFn: () => listCategories(),
    enabled: open,
  });
  const brands = useQuery({
    queryKey: ["brands", "product-options"],
    queryFn: () => listBrands(),
    enabled: open,
  });
  const settings = useQuery({
    queryKey: ["catalog-settings"],
    queryFn: getCatalogSettings,
    enabled: open,
  });
  const detail = useQuery({
    queryKey: ["product", product?.id],
    queryFn: () => getProduct(product!.id),
    enabled: open && Boolean(product),
  });
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: blankValues,
  });
  const mutation = useMutation({
    mutationFn: (values: Values) => {
      const payload: ProductPayload = {
        name: values.name,
        sku: values.sku,
        description: values.description || null,
        category_id: values.category_id,
        brand_id: values.brand_id || null,
        product_type: values.product_type as ProductType,
        requires_prescription: values.requires_prescription,
        registration_no: values.registration_no || null,
        generic_name: values.generic_name || null,
        strength: values.strength || null,
        pack_size: values.pack_size || null,
        unit: values.unit as ProductUnit,
        hsn_code: values.hsn_code || null,
        base_mrp: values.base_mrp ? Number(values.base_mrp) : null,
        low_stock_threshold: values.low_stock_threshold
          ? Number(values.low_stock_threshold)
          : null,
        is_active: values.is_active,
        is_featured: values.is_featured,
      };
      return saveProduct(payload, product?.id);
    },
    onSuccess: async (saved) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["products"] }),
        queryClient.invalidateQueries({ queryKey: ["inventory"] }),
        queryClient.invalidateQueries({ queryKey: ["product", saved.id] }),
      ]);
      toast.success(product ? "Product updated" : "Product created", {
        description: product
          ? saved.name
          : `${saved.name} is ready for images, prices, and batches.`,
      });
      if (product) setOpen(false);
      else {
        setOpen(false);
      }
    },
    onError: (error) =>
      toast.error("Product could not be saved", { description: getApiErrorDetail(error) }),
  });
  useEffect(() => {
    if (!open) return;
    const source = detail.data ?? product;
    form.reset(
      source
        ? {
            name: source.name,
            sku: source.sku,
            description: source.description ?? "",
            category_id: source.category_id,
            brand_id: source.brand_id ?? "",
            product_type: source.product_type,
            requires_prescription: source.requires_prescription,
            registration_no: source.registration_no ?? "",
            generic_name: source.generic_name ?? "",
            strength: source.strength ?? "",
            pack_size: source.pack_size ?? "",
            unit: source.unit,
            hsn_code: source.hsn_code ?? "",
            base_mrp: source.base_mrp == null ? "" : String(source.base_mrp),
            low_stock_threshold:
              source.low_stock_threshold == null ? "" : String(source.low_stock_threshold),
            is_active: source.is_active,
            is_featured: source.is_featured,
          }
        : blankValues,
    );
  }, [detail.data, form, open, product]);

  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent className="max-w-[720px]">
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Catalog
          </p>
          <DrawerTitle>{product ? "Edit product" : "Add product"}</DrawerTitle>
          <DrawerDescription>
            Maintain medicine classification, regulatory fields, selling details, and stock
            setup.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex flex-1 flex-col"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-7 px-6 py-6">
            <section aria-labelledby="product-details-heading">
              <h3 id="product-details-heading" className="mb-4 font-semibold">
                Details
              </h3>
              <div className="grid gap-5 sm:grid-cols-2">
                <FormField
                  label="Product name"
                  htmlFor="product-name"
                  error={form.formState.errors.name?.message}
                  className="sm:col-span-2"
                >
                  <Input
                    id="product-name"
                    autoFocus
                    aria-invalid={Boolean(form.formState.errors.name)}
                    {...form.register("name")}
                  />
                </FormField>
                <FormField
                  label="SKU"
                  htmlFor="product-sku"
                  error={form.formState.errors.sku?.message}
                >
                  <Input id="product-sku" className="font-mono" {...form.register("sku")} />
                </FormField>
                <FormField label="Product type" htmlFor="product-type">
                  <select
                    id="product-type"
                    className="control-base w-full"
                    {...form.register("product_type")}
                  >
                    {productTypeOptions.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField
                  label="Category"
                  htmlFor="product-category"
                  error={form.formState.errors.category_id?.message}
                >
                  <select
                    id="product-category"
                    className="control-base w-full"
                    {...form.register("category_id")}
                  >
                    <option value="">Select category</option>
                    {categories.data?.items
                      .filter((item) => item.is_active)
                      .map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.parent ? `${item.parent.name} / ` : ""}
                          {item.name}
                        </option>
                      ))}
                  </select>
                </FormField>
                <FormField label="Brand" htmlFor="product-brand">
                  <select
                    id="product-brand"
                    className="control-base w-full"
                    {...form.register("brand_id")}
                  >
                    <option value="">No brand</option>
                    {brands.data?.items
                      .filter((item) => item.is_active)
                      .map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}
                        </option>
                      ))}
                  </select>
                </FormField>
                <FormField label="Generic name" htmlFor="product-generic">
                  <Input id="product-generic" {...form.register("generic_name")} />
                </FormField>
                <FormField label="Strength" htmlFor="product-strength">
                  <Input
                    id="product-strength"
                    placeholder="e.g. 500mg"
                    {...form.register("strength")}
                  />
                </FormField>
                <FormField label="Pack size" htmlFor="product-pack">
                  <Input
                    id="product-pack"
                    placeholder="e.g. 30 tablets"
                    {...form.register("pack_size")}
                  />
                </FormField>
                <FormField label="Unit" htmlFor="product-unit">
                  <select
                    id="product-unit"
                    className="control-base w-full"
                    {...form.register("unit")}
                  >
                    {units.map((unit) => (
                      <option key={unit}>{unit}</option>
                    ))}
                  </select>
                </FormField>
                <FormField label="TMDA / registration no." htmlFor="product-registration">
                  <Input id="product-registration" {...form.register("registration_no")} />
                </FormField>
                <FormField label="HSN code" htmlFor="product-hsn">
                  <Input id="product-hsn" {...form.register("hsn_code")} />
                </FormField>
                <FormField
                  label={`Base MRP (${settings.data?.currency ?? "currency"})`}
                  htmlFor="product-mrp"
                >
                  <Input
                    id="product-mrp"
                    type="number"
                    min={0}
                    step="0.01"
                    {...form.register("base_mrp")}
                  />
                </FormField>
                <FormField
                  label="Low-stock threshold"
                  htmlFor="product-threshold"
                  hint={`Blank uses the configured default (${settings.data?.low_stock_default ?? 10}).`}
                >
                  <Input
                    id="product-threshold"
                    type="number"
                    min={0}
                    {...form.register("low_stock_threshold")}
                  />
                </FormField>
                <FormField
                  label="Description"
                  htmlFor="product-description"
                  className="sm:col-span-2"
                >
                  <textarea
                    id="product-description"
                    rows={4}
                    className="control-base h-auto w-full py-3"
                    {...form.register("description")}
                  />
                </FormField>
                <div className="grid gap-3 sm:col-span-2 sm:grid-cols-3">
                  {(
                    [
                      {
                        name: "requires_prescription",
                        label: "Prescription (POM)",
                        hint: "Requires a valid prescription.",
                      },
                      {
                        name: "is_active",
                        label: "Active",
                        hint: "Visible to operational flows.",
                      },
                      {
                        name: "is_featured",
                        label: "Featured",
                        hint: "Eligible for future highlights.",
                      },
                    ] as const
                  ).map((option) => (
                    <Controller
                      key={option.name}
                      control={form.control}
                      name={option.name}
                      render={({ field }) => (
                        <label className="flex items-start gap-3 rounded-control border border-border bg-[#FBFCFB] p-3">
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={(value) => field.onChange(Boolean(value))}
                          />
                          <span>
                            <span className="block text-sm font-semibold">
                              {option.label}
                            </span>
                            <span className="mt-0.5 block text-xs leading-5 text-secondary">
                              {option.hint}
                            </span>
                          </span>
                        </label>
                      )}
                    />
                  ))}
                </div>
              </div>
            </section>
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : product ? "Save details" : "Create product"}
            </Button>
          </DrawerFooter>
        </form>
        {detail.data ? (
          <ProductLinkedSections
            product={detail.data}
            currency={settings.data?.currency ?? "TZS"}
          />
        ) : product ? (
          <div className="border-t border-border px-6 py-6 text-sm text-secondary">
            Loading images, prices, and batches…
          </div>
        ) : (
          <div className="border-t border-border px-6 py-6">
            <h3 className="font-semibold">Images, prices & batches</h3>
            <p className="mt-1 text-sm leading-6 text-secondary">
              Create the product first, then edit it to upload imagery, enter the complete
              price matrix, and receive warehouse batches.
            </p>
          </div>
        )}
      </DrawerContent>
    </Drawer>
  );
}
