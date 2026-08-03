import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
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
import { saveCoupon } from "@/features/coupons/coupons-api";
import type { Coupon, CouponPayload } from "@/features/coupons/types";
import { getApiErrorDetail } from "@/lib/api-errors";

const schema = z
  .object({
    code: z.string().trim().min(2).max(80),
    name: z.string().trim().min(2).max(160),
    discount_type: z.enum(["PERCENT", "FLAT"]),
    discount_value: z.coerce.number().positive(),
    min_order_amount: z.union([z.literal(""), z.coerce.number().min(0)]),
    start_date: z.string().min(1, "Select a start date."),
    end_date: z.string().min(1, "Select an end date."),
    usage_limit: z.union([z.literal(""), z.coerce.number().int().positive()]),
    is_active: z.boolean(),
  })
  .superRefine((values, context) => {
    if (values.discount_type === "PERCENT" && values.discount_value > 100) {
      context.addIssue({
        code: "custom",
        path: ["discount_value"],
        message: "Percentage cannot exceed 100%.",
      });
    }
    if (values.end_date < values.start_date) {
      context.addIssue({
        code: "custom",
        path: ["end_date"],
        message: "End date must be after the start date.",
      });
    }
  });
type Values = z.infer<typeof schema>;

function defaults(coupon?: Coupon): Values {
  return {
    code: coupon?.code ?? "",
    name: coupon?.name ?? "",
    discount_type: coupon?.discount_type ?? "PERCENT",
    discount_value: coupon?.discount_value ?? 10,
    min_order_amount: coupon?.min_order_amount ?? "",
    start_date: coupon?.start_date ?? new Date().toISOString().slice(0, 10),
    end_date: coupon?.end_date ?? "",
    usage_limit: coupon?.usage_limit ?? "",
    is_active: coupon?.is_active ?? true,
  };
}

export function CouponDrawer({
  coupon,
  trigger,
}: {
  coupon?: Coupon;
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: defaults(coupon),
  });
  const save = useMutation({
    mutationFn: (payload: CouponPayload) => saveCoupon(payload, coupon?.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["coupons"] });
      toast.success(coupon ? "Coupon updated" : "Coupon created");
      setOpen(false);
    },
    onError: (error) =>
      toast.error("Coupon could not be saved", { description: getApiErrorDetail(error) }),
  });
  useEffect(() => {
    if (open) form.reset(defaults(coupon));
  }, [coupon, form, open]);
  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Commercial controls
          </p>
          <DrawerTitle>{coupon ? "Edit coupon" : "Create coupon"}</DrawerTitle>
          <DrawerDescription>
            Validity and usage limits are enforced server-side when an order is confirmed.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex min-h-0 flex-1 flex-col"
          onSubmit={form.handleSubmit((values) =>
            save.mutate({
              ...values,
              code: values.code.toUpperCase(),
              min_order_amount:
                values.min_order_amount === "" ? null : Number(values.min_order_amount),
              usage_limit: values.usage_limit === "" ? null : Number(values.usage_limit),
            }),
          )}
        >
          <div className="scrollbar-subtle flex-1 space-y-4 overflow-y-auto px-6 py-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                label="Code"
                htmlFor="coupon-code"
                error={form.formState.errors.code?.message}
              >
                <Input
                  id="coupon-code"
                  autoFocus
                  className="font-mono uppercase"
                  {...form.register("code")}
                />
              </FormField>
              <FormField
                label="Name"
                htmlFor="coupon-name"
                error={form.formState.errors.name?.message}
              >
                <Input id="coupon-name" {...form.register("name")} />
              </FormField>
              <FormField label="Discount type" htmlFor="coupon-type">
                <select
                  id="coupon-type"
                  className="control-base w-full"
                  {...form.register("discount_type")}
                >
                  <option value="PERCENT">Percentage</option>
                  <option value="FLAT">Flat amount</option>
                </select>
              </FormField>
              <FormField
                label="Discount value"
                htmlFor="coupon-value"
                error={form.formState.errors.discount_value?.message}
              >
                <Input
                  id="coupon-value"
                  type="number"
                  min="0.01"
                  step="0.01"
                  {...form.register("discount_value")}
                />
              </FormField>
              <FormField label="Minimum order" htmlFor="coupon-min">
                <Input
                  id="coupon-min"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="No minimum"
                  {...form.register("min_order_amount")}
                />
              </FormField>
              <FormField label="Usage limit" htmlFor="coupon-limit">
                <Input
                  id="coupon-limit"
                  type="number"
                  min="1"
                  placeholder="Unlimited"
                  {...form.register("usage_limit")}
                />
              </FormField>
              <FormField label="Start date" htmlFor="coupon-start">
                <Input id="coupon-start" type="date" {...form.register("start_date")} />
              </FormField>
              <FormField
                label="End date"
                htmlFor="coupon-end"
                error={form.formState.errors.end_date?.message}
              >
                <Input id="coupon-end" type="date" {...form.register("end_date")} />
              </FormField>
            </div>
            <label className="flex cursor-pointer items-center gap-3 rounded-control border border-border bg-background p-3 text-sm font-semibold">
              <input
                type="checkbox"
                className="size-4 accent-primary-700"
                {...form.register("is_active")}
              />
              Coupon is active
            </label>
          </div>
          <DrawerFooter>
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? "Saving…" : coupon ? "Save changes" : "Create coupon"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
