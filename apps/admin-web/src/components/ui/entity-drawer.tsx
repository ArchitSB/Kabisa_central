import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, MapPin, ShoppingBasket } from "lucide-react";
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
import { Input } from "@/components/ui/input";

const orderPreviewSchema = z.object({
  customer: z.string().min(1, "Select a customer."),
  deliveryLocation: z.string().min(3, "Enter a delivery location."),
  note: z.string().max(240, "Keep notes under 240 characters.").optional(),
});

type OrderPreviewValues = z.infer<typeof orderPreviewSchema>;

type EntityDrawerProps = {
  trigger: React.ReactNode;
};

export function EntityDrawer({ trigger }: EntityDrawerProps) {
  const [open, setOpen] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<OrderPreviewValues>({
    resolver: zodResolver(orderPreviewSchema),
    defaultValues: {
      customer: "",
      deliveryLocation: "",
      note: "",
    },
  });

  function onSubmit(values: OrderPreviewValues) {
    toast.success("Order draft captured for this preview", {
      description: `${values.customer} · Live pricing and stock checks arrive in Phase 4.`,
    });
    reset();
    setOpen(false);
  }

  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Preview form
          </p>
          <DrawerTitle>Create an order</DrawerTitle>
          <DrawerDescription>
            This validates the shared drawer and form language. Server-priced line items and
            live stock checks are scheduled for Phase 4.
          </DrawerDescription>
        </DrawerHeader>

        <form
          id="order-preview-form"
          className="flex flex-1 flex-col"
          onSubmit={handleSubmit(onSubmit)}
        >
          <div className="space-y-6 px-6 py-6">
            <div>
              <label
                htmlFor="customer"
                className="mb-2 block text-sm font-semibold text-foreground"
              >
                Customer
              </label>
              <div className="relative">
                <Building2
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
                />
                <select
                  id="customer"
                  className="control-base w-full appearance-none pl-10"
                  aria-invalid={Boolean(errors.customer)}
                  {...register("customer")}
                >
                  <option value="">Select a verified customer</option>
                  <option value="Upendo Community Pharmacy">
                    Upendo Community Pharmacy
                  </option>
                  <option value="AfyaPlus DLDM">AfyaPlus DLDM</option>
                  <option value="Mwanza Medical Stores">Mwanza Medical Stores</option>
                </select>
              </div>
              {errors.customer ? (
                <p className="mt-1.5 text-xs font-medium text-danger">
                  {errors.customer.message}
                </p>
              ) : (
                <p className="mt-1.5 text-xs text-secondary">
                  Ordering will be restricted to verified customers.
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="deliveryLocation"
                className="mb-2 block text-sm font-semibold text-foreground"
              >
                Delivery location
              </label>
              <div className="relative">
                <MapPin
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
                />
                <Input
                  id="deliveryLocation"
                  className="pl-10"
                  placeholder="e.g. Kinondoni, Dar es Salaam"
                  aria-invalid={Boolean(errors.deliveryLocation)}
                  {...register("deliveryLocation")}
                />
              </div>
              {errors.deliveryLocation ? (
                <p className="mt-1.5 text-xs font-medium text-danger">
                  {errors.deliveryLocation.message}
                </p>
              ) : null}
            </div>

            <div>
              <label
                htmlFor="note"
                className="mb-2 block text-sm font-semibold text-foreground"
              >
                Internal note <span className="font-normal text-muted">(optional)</span>
              </label>
              <textarea
                id="note"
                rows={4}
                className="control-base h-auto w-full resize-y py-3"
                placeholder="Add context for the sales or delivery team"
                aria-invalid={Boolean(errors.note)}
                {...register("note")}
              />
              {errors.note ? (
                <p className="mt-1.5 text-xs font-medium text-danger">
                  {errors.note.message}
                </p>
              ) : null}
            </div>

            <div className="rounded-card border border-primary-200 bg-primary-50 p-4">
              <div className="flex gap-3">
                <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary-100 text-primary-800">
                  <ShoppingBasket aria-hidden="true" className="size-4" />
                </span>
                <div>
                  <p className="text-sm font-semibold text-primary-900">Next: line items</p>
                  <p className="mt-1 text-xs leading-5 text-primary-800">
                    Customer-tier pricing, stock availability, coupons, and totals are
                    always computed by the API—not this form.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button type="submit" disabled={isSubmitting}>
              Save preview
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
