import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Plus, TicketPercent, Trash2, X } from "lucide-react";
import { useFieldArray, useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { listProducts, listWarehouses } from "@/features/catalog/catalog-api";
import { listCustomers } from "@/features/customers/customers-api";
import { useHasPermission } from "@/features/auth/auth-store";
import { validateCoupon } from "@/features/coupons/coupons-api";
import { createOrder, previewOrder } from "@/features/orders/orders-api";
import type { OrderPayload } from "@/features/orders/orders.data";
import { getApiErrorDetail } from "@/lib/api-errors";
import { formatMoney } from "@/lib/utils";

const schema = z.object({
  customer_id: z.string().uuid("Select a verified customer."),
  warehouse_id: z.string().uuid("Select a warehouse."),
  items: z
    .array(
      z.object({
        product_id: z.string().uuid("Select a product."),
        quantity: z.coerce.number().int().positive("Quantity must be at least 1."),
        line_discount: z.coerce.number().min(0),
      }),
    )
    .min(1, "Add at least one product."),
  discount_total: z.coerce.number().min(0),
  tax_total: z.coerce.number().min(0),
  coupon_code: z.string().trim(),
  delivery_address: z.string().trim(),
  delivery_location: z.string().trim(),
  notes: z.string().trim(),
});
type Values = z.infer<typeof schema>;

export function CreateOrderDrawer({ trigger }: { trigger: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [couponEntry, setCouponEntry] = useState("");
  const [couponMessage, setCouponMessage] = useState<string | null>(null);
  const navigate = useNavigate();
  const canUseCoupons = useHasPermission("coupons.view");
  const queryClient = useQueryClient();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      customer_id: "",
      warehouse_id: "",
      items: [{ product_id: "", quantity: 1, line_discount: 0 }],
      discount_total: 0,
      tax_total: 0,
      coupon_code: "",
      delivery_address: "",
      delivery_location: "",
      notes: "",
    },
  });
  const lines = useFieldArray({ control: form.control, name: "items" });
  const values = form.watch();
  const customers = useQuery({
    queryKey: ["customers", "verified-order-options"],
    queryFn: () => listCustomers({ status: "VERIFIED" }),
    enabled: open,
  });
  const warehouses = useQuery({
    queryKey: ["warehouses", "order-options"],
    queryFn: () => listWarehouses(),
    enabled: open,
  });
  const products = useQuery({
    queryKey: ["products", "order-options", values.warehouse_id],
    queryFn: () =>
      listProducts({
        warehouse_id: values.warehouse_id || undefined,
        is_active: true,
      }),
    enabled: open && Boolean(values.warehouse_id),
  });
  const payload = useMemo<OrderPayload | null>(() => {
    if (
      !values.customer_id ||
      !values.warehouse_id ||
      !values.items.length ||
      values.items.some((line) => !line.product_id || line.quantity < 1)
    ) {
      return null;
    }
    return {
      customer_id: values.customer_id,
      warehouse_id: values.warehouse_id,
      items: values.items,
      discount_total: values.discount_total,
      tax_total: values.tax_total,
      coupon_code: values.coupon_code || null,
      delivery_address: values.delivery_address || null,
      delivery_location: values.delivery_location || null,
      notes: values.notes || null,
    };
  }, [values]);
  const preview = useQuery({
    queryKey: ["order-preview", payload],
    queryFn: () => previewOrder(payload as OrderPayload),
    enabled: open && Boolean(payload),
    retry: false,
  });
  const save = useMutation({
    mutationFn: createOrder,
    onSuccess: async (order) => {
      await queryClient.invalidateQueries({ queryKey: ["orders"] });
      toast.success("Order created", { description: order.order_number });
      setOpen(false);
      navigate(`/orders/${order.id}`);
    },
    onError: (error) =>
      toast.error("Order could not be created", { description: getApiErrorDetail(error) }),
  });
  const applyCoupon = useMutation({
    mutationFn: () => validateCoupon(couponEntry, preview.data?.subtotal ?? 0),
    onSuccess: (result) => {
      if (!result.valid || !result.code) {
        form.setValue("coupon_code", "");
        setCouponMessage(result.reason ?? "This coupon is not valid.");
        return;
      }
      form.setValue("coupon_code", result.code, { shouldDirty: true });
      setCouponEntry(result.code);
      setCouponMessage(`Applied · ${result.code}`);
    },
    onError: (error) => setCouponMessage(getApiErrorDetail(error)),
  });

  useEffect(() => {
    if (!open) {
      form.reset();
      setCouponEntry("");
      setCouponMessage(null);
    }
  }, [form, open]);

  function selectCustomer(id: string) {
    form.setValue("customer_id", id, { shouldValidate: true });
    const customer = customers.data?.items.find((item) => item.id === id);
    if (customer) {
      form.setValue("delivery_address", customer.physical_address);
      form.setValue("delivery_location", customer.region ?? "");
    }
  }

  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent className="max-w-[760px]">
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Verified customer order
          </p>
          <DrawerTitle>Create order</DrawerTitle>
          <DrawerDescription>
            Prices, stock checks, discounts, tax, and totals are resolved by the server.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex min-h-0 flex-1 flex-col"
          noValidate
          onSubmit={form.handleSubmit((data) =>
            save.mutate({
              ...data,
              delivery_address: data.delivery_address || null,
              delivery_location: data.delivery_location || null,
              notes: data.notes || null,
            }),
          )}
        >
          <div className="scrollbar-subtle flex-1 space-y-6 overflow-y-auto px-6 py-6">
            <section className="grid gap-4 sm:grid-cols-2">
              <FormField
                label="Verified customer"
                htmlFor="order-customer"
                error={form.formState.errors.customer_id?.message}
              >
                <select
                  id="order-customer"
                  autoFocus
                  className="control-base w-full"
                  value={values.customer_id}
                  onChange={(event) => selectCustomer(event.target.value)}
                >
                  <option value="">Select customer</option>
                  {customers.data?.items.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.business_name} · {customer.price_tier.code}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField
                label="Fulfilling warehouse"
                htmlFor="order-warehouse"
                error={form.formState.errors.warehouse_id?.message}
              >
                <select
                  id="order-warehouse"
                  className="control-base w-full"
                  {...form.register("warehouse_id")}
                >
                  <option value="">Select warehouse</option>
                  {warehouses.data?.items
                    .filter((item) => item.is_active)
                    .map((warehouse) => (
                      <option key={warehouse.id} value={warehouse.id}>
                        {warehouse.name}
                      </option>
                    ))}
                </select>
              </FormField>
            </section>

            <section className="border-t border-border pt-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-bold">Line items</h3>
                  <p className="text-xs text-secondary">
                    On-hand is scoped to the selected warehouse.
                  </p>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    lines.append({ product_id: "", quantity: 1, line_discount: 0 })
                  }
                >
                  <Plus aria-hidden="true" /> Add line
                </Button>
              </div>
              <div className="space-y-3">
                {lines.fields.map((field, index) => {
                  const chosen = products.data?.items.find(
                    (item) => item.id === values.items[index]?.product_id,
                  );
                  return (
                    <div
                      key={field.id}
                      className="grid gap-3 rounded-card border border-border bg-background p-4 sm:grid-cols-[minmax(0,1fr)_100px_130px_auto]"
                    >
                      <FormField label="Product" htmlFor={`order-product-${index}`}>
                        <select
                          id={`order-product-${index}`}
                          className="control-base w-full"
                          {...form.register(`items.${index}.product_id`)}
                        >
                          <option value="">Select product</option>
                          {products.data?.items.map((product) => (
                            <option
                              key={product.id}
                              value={product.id}
                              disabled={product.on_hand < 1}
                            >
                              {product.name} · {product.sku} · {product.on_hand} on-hand
                            </option>
                          ))}
                        </select>
                        {chosen ? (
                          <span className="mt-1 block text-xs text-secondary">
                            {chosen.on_hand} available
                          </span>
                        ) : null}
                      </FormField>
                      <FormField label="Qty" htmlFor={`order-qty-${index}`}>
                        <Input
                          id={`order-qty-${index}`}
                          type="number"
                          min="1"
                          max={chosen?.on_hand}
                          {...form.register(`items.${index}.quantity`)}
                        />
                      </FormField>
                      <FormField label="Line discount" htmlFor={`order-discount-${index}`}>
                        <Input
                          id={`order-discount-${index}`}
                          type="number"
                          min="0"
                          step="0.01"
                          {...form.register(`items.${index}.line_discount`)}
                        />
                      </FormField>
                      <div className="flex items-end">
                        <Button
                          type="button"
                          variant="destructive"
                          size="icon"
                          aria-label={`Remove line ${index + 1}`}
                          disabled={lines.fields.length === 1}
                          onClick={() => lines.remove(index)}
                        >
                          <Trash2 aria-hidden="true" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="grid gap-4 border-t border-border pt-6 sm:grid-cols-2">
              <FormField label="Delivery address" htmlFor="order-address">
                <textarea
                  id="order-address"
                  rows={3}
                  className="control-base h-auto w-full py-3"
                  {...form.register("delivery_address")}
                />
              </FormField>
              <div className="space-y-4">
                <FormField label="Delivery location" htmlFor="order-location">
                  <Input id="order-location" {...form.register("delivery_location")} />
                </FormField>
                <FormField label="Notes" htmlFor="order-notes">
                  <Input id="order-notes" {...form.register("notes")} />
                </FormField>
              </div>
            </section>

            {canUseCoupons ? (
              <section className="border-t border-border pt-6">
                <FormField label="Coupon (optional)" htmlFor="order-coupon">
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <div className="relative flex-1">
                      <TicketPercent
                        aria-hidden="true"
                        className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
                      />
                      <Input
                        id="order-coupon"
                        className="pl-10 font-mono uppercase"
                        value={couponEntry}
                        placeholder="Enter coupon code"
                        onChange={(event) => {
                          setCouponEntry(event.target.value.toUpperCase());
                          setCouponMessage(null);
                        }}
                      />
                    </div>
                    {values.coupon_code ? (
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => {
                          form.setValue("coupon_code", "");
                          setCouponEntry("");
                          setCouponMessage(null);
                        }}
                      >
                        <X aria-hidden="true" /> Remove
                      </Button>
                    ) : (
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={!couponEntry || !preview.data || applyCoupon.isPending}
                        onClick={() => applyCoupon.mutate()}
                      >
                        {applyCoupon.isPending ? "Checking…" : "Apply coupon"}
                      </Button>
                    )}
                  </div>
                  {couponMessage ? (
                    <span
                      className={`mt-2 flex items-center gap-1.5 text-xs font-semibold ${values.coupon_code ? "text-success" : "text-danger"}`}
                    >
                      {values.coupon_code ? (
                        <CheckCircle2 aria-hidden="true" className="size-4" />
                      ) : null}
                      {couponMessage}
                    </span>
                  ) : null}
                </FormField>
              </section>
            ) : null}

            <section className="grid gap-4 border-t border-border pt-6 sm:grid-cols-2">
              <FormField label="Order discount" htmlFor="order-discount-total">
                <Input
                  id="order-discount-total"
                  type="number"
                  min="0"
                  {...form.register("discount_total")}
                />
              </FormField>
              <FormField label="Tax total" htmlFor="order-tax-total">
                <Input
                  id="order-tax-total"
                  type="number"
                  min="0"
                  {...form.register("tax_total")}
                />
              </FormField>
            </section>

            <section
              aria-live="polite"
              className="rounded-card border border-primary-200 bg-primary-50 p-4"
            >
              {preview.isFetching ? (
                <p className="text-sm text-secondary">Checking prices and stock…</p>
              ) : null}
              {preview.isError ? (
                <p className="text-sm font-medium text-danger">
                  {getApiErrorDetail(preview.error)}
                </p>
              ) : null}
              {preview.data ? (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Price tier</span>
                    <strong>{preview.data.price_tier_code}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Subtotal</span>
                    <strong>
                      {formatMoney(preview.data.subtotal, preview.data.currency)}
                    </strong>
                  </div>
                  <div className="flex justify-between text-secondary">
                    <span>Total discounts</span>
                    <strong>
                      −{formatMoney(preview.data.discount_total, preview.data.currency)}
                    </strong>
                  </div>
                  {preview.data.coupon_code ? (
                    <div className="flex justify-between text-success">
                      <span>Coupon · {preview.data.coupon_code}</span>
                      <strong>
                        −{formatMoney(preview.data.coupon_discount, preview.data.currency)}
                      </strong>
                    </div>
                  ) : null}
                  <div className="flex justify-between border-t border-primary-200 pt-2 text-base">
                    <span>Total</span>
                    <strong>
                      {formatMoney(preview.data.total_amount, preview.data.currency)}
                    </strong>
                  </div>
                </div>
              ) : null}
            </section>
          </div>
          <DrawerFooter>
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={save.isPending || !preview.data || preview.isError}
            >
              {save.isPending ? "Creating…" : "Create pending order"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
