import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
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
  adjustBatch,
  createBatch,
  getCatalogSettings,
  listProducts,
  listWarehouses,
} from "@/features/catalog/catalog-api";
import type { ProductBatch } from "@/features/catalog/types";
import { getApiErrorDetail } from "@/lib/api-errors";

const inboundSchema = z.object({
  product_id: z.string().uuid("Select a product."),
  warehouse_id: z.string().uuid("Select a warehouse."),
  batch_number: z.string().trim().min(1, "Enter a batch number."),
  expiry_date: z.string().min(1, "Select an expiry date."),
  received_date: z.string().min(1),
  quantity_available: z.coerce.number().int().positive("Enter a positive quantity."),
  cost_price: z.string(),
  note: z.string(),
});
type InboundValues = z.infer<typeof inboundSchema>;
const adjustSchema = z.object({
  delta: z.coerce
    .number()
    .int()
    .refine((value) => value !== 0, "Enter a non-zero adjustment."),
  note: z.string().trim().min(3, "Explain the stock adjustment."),
});
type AdjustValues = z.infer<typeof adjustSchema>;

function useInventoryRefresh() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["inventory"] }),
      queryClient.invalidateQueries({ queryKey: ["products"] }),
      queryClient.invalidateQueries({ queryKey: ["product"] }),
      queryClient.invalidateQueries({ queryKey: ["batches"] }),
    ]);
}

export function InboundBatchDrawer({
  trigger,
  productId = "",
}: {
  trigger: React.ReactNode;
  productId?: string;
}) {
  const [open, setOpen] = useState(false);
  const refresh = useInventoryRefresh();
  const products = useQuery({
    queryKey: ["products", "batch-options"],
    queryFn: () => listProducts(),
    enabled: open,
  });
  const warehouses = useQuery({
    queryKey: ["warehouses", "batch-options"],
    queryFn: () => listWarehouses(),
    enabled: open,
  });
  const settings = useQuery({
    queryKey: ["catalog-settings"],
    queryFn: getCatalogSettings,
    enabled: open,
  });
  const form = useForm<InboundValues>({
    resolver: zodResolver(inboundSchema),
    defaultValues: {
      product_id: productId,
      warehouse_id: "",
      batch_number: "",
      expiry_date: "",
      received_date: new Date().toISOString().slice(0, 10),
      quantity_available: 1,
      cost_price: "",
      note: "",
    },
  });
  useEffect(() => {
    if (open)
      form.reset({
        product_id: productId,
        warehouse_id: "",
        batch_number: "",
        expiry_date: "",
        received_date: new Date().toISOString().slice(0, 10),
        quantity_available: 1,
        cost_price: "",
        note: "",
      });
  }, [form, open, productId]);
  const mutation = useMutation({
    mutationFn: (values: InboundValues) =>
      createBatch({
        product_id: values.product_id,
        warehouse_id: values.warehouse_id,
        batch_number: values.batch_number,
        expiry_date: values.expiry_date,
        received_date: values.received_date,
        quantity_available: values.quantity_available,
        cost_price: values.cost_price ? Number(values.cost_price) : null,
        note: values.note || null,
      }),
    onSuccess: async (saved) => {
      await refresh();
      toast.success("Inbound batch recorded", {
        description: `${saved.product_name} · ${saved.quantity_available} units`,
      });
      setOpen(false);
    },
    onError: (error) =>
      toast.error("Batch could not be recorded", { description: getApiErrorDetail(error) }),
  });
  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Inventory receipt
          </p>
          <DrawerTitle>Add inbound batch</DrawerTitle>
          <DrawerDescription>
            Receive dated stock into one warehouse and write the opening movement.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex flex-1 flex-col"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="grid gap-5 px-6 py-6 sm:grid-cols-2">
            <FormField
              label="Product"
              htmlFor="inbound-product"
              error={form.formState.errors.product_id?.message}
              className="sm:col-span-2"
            >
              <select
                id="inbound-product"
                className="control-base w-full"
                disabled={Boolean(productId)}
                {...form.register("product_id")}
              >
                <option value="">Select product</option>
                {products.data?.items
                  .filter((item) => item.is_active)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} · {item.sku}
                    </option>
                  ))}
              </select>
            </FormField>
            <FormField
              label="Warehouse"
              htmlFor="inbound-warehouse"
              error={form.formState.errors.warehouse_id?.message}
              className="sm:col-span-2"
            >
              <select
                id="inbound-warehouse"
                className="control-base w-full"
                {...form.register("warehouse_id")}
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
              htmlFor="inbound-number"
              error={form.formState.errors.batch_number?.message}
            >
              <Input id="inbound-number" {...form.register("batch_number")} />
            </FormField>
            <FormField
              label="Quantity"
              htmlFor="inbound-quantity"
              error={form.formState.errors.quantity_available?.message}
            >
              <Input
                id="inbound-quantity"
                type="number"
                min={1}
                {...form.register("quantity_available")}
              />
            </FormField>
            <FormField
              label="Expiry date"
              htmlFor="inbound-expiry"
              error={form.formState.errors.expiry_date?.message}
            >
              <Input id="inbound-expiry" type="date" {...form.register("expiry_date")} />
            </FormField>
            <FormField label="Received date" htmlFor="inbound-received">
              <Input
                id="inbound-received"
                type="date"
                {...form.register("received_date")}
              />
            </FormField>
            <FormField
              label={`Unit cost (${settings.data?.currency ?? "currency"})`}
              htmlFor="inbound-cost"
            >
              <Input
                id="inbound-cost"
                type="number"
                min={0}
                step="0.01"
                {...form.register("cost_price")}
              />
            </FormField>
            <FormField label="Receiving note" htmlFor="inbound-note">
              <Input id="inbound-note" {...form.register("note")} />
            </FormField>
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Recording…" : "Record inbound"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}

export function AdjustBatchDrawer({
  trigger,
  batch,
}: {
  trigger: React.ReactNode;
  batch: ProductBatch;
}) {
  const [open, setOpen] = useState(false);
  const refresh = useInventoryRefresh();
  const form = useForm<AdjustValues>({
    resolver: zodResolver(adjustSchema),
    defaultValues: { delta: 0, note: "" },
  });
  useEffect(() => {
    if (open) form.reset({ delta: 0, note: "" });
  }, [form, open]);
  const mutation = useMutation({
    mutationFn: (values: AdjustValues) => adjustBatch(batch.id, values.delta, values.note),
    onSuccess: async (saved) => {
      await refresh();
      toast.success("Stock adjusted", {
        description: `${saved.product_name} · ${saved.quantity_available} available`,
      });
      setOpen(false);
    },
    onError: (error) =>
      toast.error("Stock could not be adjusted", { description: getApiErrorDetail(error) }),
  });
  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Stock control
          </p>
          <DrawerTitle>Adjust batch</DrawerTitle>
          <DrawerDescription>
            {batch.product_name} · {batch.warehouse_name} · {batch.batch_number}
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex flex-1 flex-col"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-5 px-6 py-6">
            <div className="rounded-control border border-border bg-[#FBFCFB] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.06em] text-secondary">
                Current available
              </p>
              <p className="numeric mt-1 font-display text-3xl font-semibold">
                {batch.quantity_available}
              </p>
              <p className="mt-1 text-xs text-secondary">
                Reserved: {batch.quantity_reserved}
              </p>
            </div>
            <FormField
              label="Adjustment delta"
              htmlFor={`adjust-delta-${batch.id}`}
              error={form.formState.errors.delta?.message}
              hint="Positive adds stock; negative removes stock. Available stock can never fall below reserved stock."
            >
              <Input
                id={`adjust-delta-${batch.id}`}
                type="number"
                autoFocus
                {...form.register("delta")}
              />
            </FormField>
            <FormField
              label="Reason"
              htmlFor={`adjust-note-${batch.id}`}
              error={form.formState.errors.note?.message}
            >
              <textarea
                id={`adjust-note-${batch.id}`}
                rows={4}
                className="control-base h-auto w-full py-3"
                {...form.register("note")}
              />
            </FormField>
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Adjusting…" : "Apply adjustment"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
