import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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
import { saveWarehouse } from "@/features/catalog/catalog-api";
import type { Warehouse } from "@/features/catalog/types";
import { getApiErrorDetail } from "@/lib/api-errors";

const schema = z.object({
  name: z.string().trim().min(2, "Enter a warehouse name."),
  code: z.string().trim().min(2, "Enter a short warehouse code."),
  address: z.string().trim().min(4, "Enter the physical address."),
  region: z.string().trim().min(2, "Enter the region."),
  is_primary: z.boolean(),
  is_active: z.boolean(),
});
type Values = z.infer<typeof schema>;

export function WarehouseDrawer({
  trigger,
  warehouse,
}: {
  trigger: React.ReactNode;
  warehouse?: Warehouse;
}) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      code: "",
      address: "",
      region: "Dar es Salaam",
      is_primary: false,
      is_active: true,
    },
  });
  const mutation = useMutation({
    mutationFn: (values: Values) => saveWarehouse(values, warehouse?.id),
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: ["warehouses"] });
      toast.success(warehouse ? "Warehouse updated" : "Warehouse created", {
        description: saved.name,
      });
      setOpen(false);
    },
    onError: (error) =>
      toast.error("Warehouse could not be saved", {
        description: getApiErrorDetail(error),
      }),
  });

  useEffect(() => {
    if (open) {
      form.reset({
        name: warehouse?.name ?? "",
        code: warehouse?.code ?? "",
        address: warehouse?.address ?? "",
        region: warehouse?.region ?? "Dar es Salaam",
        is_primary: warehouse?.is_primary ?? false,
        is_active: warehouse?.is_active ?? true,
      });
    }
  }, [form, open, warehouse]);

  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Inventory setup
          </p>
          <DrawerTitle>{warehouse ? "Edit warehouse" : "Add warehouse"}</DrawerTitle>
          <DrawerDescription>
            Maintain a physical stock location and its operational status.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex flex-1 flex-col"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="grid gap-5 px-6 py-6 sm:grid-cols-2">
            <FormField
              label="Name"
              htmlFor="warehouse-name"
              error={form.formState.errors.name?.message}
              className="sm:col-span-2"
            >
              <Input
                id="warehouse-name"
                autoFocus
                aria-invalid={Boolean(form.formState.errors.name)}
                {...form.register("name")}
              />
            </FormField>
            <FormField
              label="Code"
              htmlFor="warehouse-code"
              error={form.formState.errors.code?.message}
              hint="Saved in uppercase with underscores."
            >
              <Input
                id="warehouse-code"
                aria-invalid={Boolean(form.formState.errors.code)}
                {...form.register("code")}
              />
            </FormField>
            <FormField
              label="Region"
              htmlFor="warehouse-region"
              error={form.formState.errors.region?.message}
            >
              <Input
                id="warehouse-region"
                aria-invalid={Boolean(form.formState.errors.region)}
                {...form.register("region")}
              />
            </FormField>
            <FormField
              label="Address"
              htmlFor="warehouse-address"
              error={form.formState.errors.address?.message}
              className="sm:col-span-2"
            >
              <textarea
                id="warehouse-address"
                rows={4}
                className="control-base h-auto w-full py-3"
                aria-invalid={Boolean(form.formState.errors.address)}
                {...form.register("address")}
              />
            </FormField>
            {(["is_primary", "is_active"] as const).map((name) => (
              <Controller
                key={name}
                control={form.control}
                name={name}
                render={({ field }) => (
                  <label className="flex items-start gap-3 rounded-control border border-border bg-[#FBFCFB] p-4">
                    <Checkbox
                      checked={field.value}
                      disabled={Boolean(
                        warehouse?.is_primary &&
                        (name === "is_primary" || name === "is_active"),
                      )}
                      onCheckedChange={(value) => field.onChange(Boolean(value))}
                    />
                    <span>
                      <span className="block text-sm font-semibold">
                        {name === "is_primary" ? "Primary warehouse" : "Active location"}
                      </span>
                      <span className="mt-0.5 block text-xs leading-5 text-secondary">
                        {name === "is_primary"
                          ? warehouse?.is_primary
                            ? "Set another row as primary before changing this designation."
                            : "Default location for operational views."
                          : warehouse?.is_primary
                            ? "The primary location must remain active."
                            : "Available for receiving and adjustments."}
                      </span>
                    </span>
                  </label>
                )}
              />
            ))}
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : "Save warehouse"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
