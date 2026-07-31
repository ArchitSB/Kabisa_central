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
import { saveBrand } from "@/features/catalog/catalog-api";
import type { Brand } from "@/features/catalog/types";
import { getApiErrorDetail } from "@/lib/api-errors";

const schema = z.object({
  name: z.string().trim().min(2, "Enter a brand name."),
  logo_path: z.string(),
  is_active: z.boolean(),
});
type Values = z.infer<typeof schema>;

export function BrandDrawer({
  trigger,
  brand,
}: {
  trigger: React.ReactNode;
  brand?: Brand;
}) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", logo_path: "", is_active: true },
  });
  const mutation = useMutation({
    mutationFn: (values: Values) =>
      saveBrand(
        {
          name: values.name,
          logo_path: values.logo_path || null,
          is_active: values.is_active,
        },
        brand?.id,
      ),
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: ["brands"] });
      toast.success(brand ? "Brand updated" : "Brand created", { description: saved.name });
      setOpen(false);
    },
    onError: (error) =>
      toast.error("Brand could not be saved", { description: getApiErrorDetail(error) }),
  });
  useEffect(() => {
    if (open)
      form.reset({
        name: brand?.name ?? "",
        logo_path: brand?.logo_path ?? "",
        is_active: brand?.is_active ?? true,
      });
  }, [brand, form, open]);
  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Catalog partners
          </p>
          <DrawerTitle>{brand ? "Edit brand" : "Add brand"}</DrawerTitle>
          <DrawerDescription>
            Maintain manufacturer and Kabisa-owned brand records.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex flex-1 flex-col"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-5 px-6 py-6">
            <FormField
              label="Brand name"
              htmlFor="brand-name"
              error={form.formState.errors.name?.message}
            >
              <Input
                id="brand-name"
                autoFocus
                aria-invalid={Boolean(form.formState.errors.name)}
                {...form.register("name")}
              />
            </FormField>
            <FormField
              label="Logo path"
              htmlFor="brand-logo"
              hint="Optional hosted or local logo path."
            >
              <Input id="brand-logo" {...form.register("logo_path")} />
            </FormField>
            <Controller
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <label className="flex items-start gap-3 rounded-control border border-border bg-[#FBFCFB] p-4">
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={(value) => field.onChange(Boolean(value))}
                  />
                  <span>
                    <span className="block text-sm font-semibold">Active brand</span>
                    <span className="mt-0.5 block text-xs leading-5 text-secondary">
                      Available for product assignment and filtering.
                    </span>
                  </span>
                </label>
              )}
            />
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : "Save brand"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
