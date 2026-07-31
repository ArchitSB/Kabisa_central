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
import { listCategories, saveCategory } from "@/features/catalog/catalog-api";
import type { Category } from "@/features/catalog/types";
import { getApiErrorDetail } from "@/lib/api-errors";

const schema = z.object({
  name: z.string().trim().min(2, "Enter a category name."),
  parent_id: z.string(),
  image_path: z.string(),
  description: z.string().max(2000),
  sort_order: z.coerce.number().int().min(0),
  is_active: z.boolean(),
});
type Values = z.infer<typeof schema>;

export function CategoryDrawer({
  trigger,
  category,
}: {
  trigger: React.ReactNode;
  category?: Category;
}) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const categories = useQuery({
    queryKey: ["categories", "drawer-options"],
    queryFn: () => listCategories(),
    enabled: open,
  });
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      parent_id: "",
      image_path: "",
      description: "",
      sort_order: 0,
      is_active: true,
    },
  });
  const mutation = useMutation({
    mutationFn: (values: Values) =>
      saveCategory(
        {
          name: values.name,
          parent_id: values.parent_id || null,
          image_path: values.image_path || null,
          description: values.description || null,
          sort_order: values.sort_order,
          is_active: values.is_active,
        },
        category?.id,
      ),
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: ["categories"] });
      toast.success(category ? "Category updated" : "Category created", {
        description: saved.name,
      });
      setOpen(false);
    },
    onError: (error) =>
      toast.error("Category could not be saved", { description: getApiErrorDetail(error) }),
  });
  useEffect(() => {
    if (open)
      form.reset({
        name: category?.name ?? "",
        parent_id: category?.parent_id ?? "",
        image_path: category?.image_path ?? "",
        description: category?.description ?? "",
        sort_order: category?.sort_order ?? 0,
        is_active: category?.is_active ?? true,
      });
  }, [category, form, open]);

  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Catalog structure
          </p>
          <DrawerTitle>{category ? "Edit category" : "Add category"}</DrawerTitle>
          <DrawerDescription>
            Create a therapeutic group or nest it under another category.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex flex-1 flex-col"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-5 px-6 py-6">
            <FormField
              label="Category name"
              htmlFor="category-name"
              error={form.formState.errors.name?.message}
            >
              <Input
                id="category-name"
                autoFocus
                aria-invalid={Boolean(form.formState.errors.name)}
                {...form.register("name")}
              />
            </FormField>
            <FormField
              label="Parent category"
              htmlFor="category-parent"
              hint="Leave blank for a top-level category."
            >
              <select
                id="category-parent"
                className="control-base w-full"
                {...form.register("parent_id")}
              >
                <option value="">No parent</option>
                {categories.data?.items
                  .filter((item) => item.id !== category?.id)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
              </select>
            </FormField>
            <FormField label="Description" htmlFor="category-description">
              <textarea
                id="category-description"
                rows={4}
                className="control-base h-auto w-full py-3"
                {...form.register("description")}
              />
            </FormField>
            <div className="grid gap-5 sm:grid-cols-2">
              <FormField
                label="Image path"
                htmlFor="category-image"
                hint="Optional hosted or local image path."
              >
                <Input id="category-image" {...form.register("image_path")} />
              </FormField>
              <FormField
                label="Sort order"
                htmlFor="category-sort"
                error={form.formState.errors.sort_order?.message}
              >
                <Input
                  id="category-sort"
                  type="number"
                  min={0}
                  {...form.register("sort_order")}
                />
              </FormField>
            </div>
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
                    <span className="block text-sm font-semibold">Active category</span>
                    <span className="mt-0.5 block text-xs leading-5 text-secondary">
                      Available when creating and filtering products.
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
              {mutation.isPending ? "Saving…" : "Save category"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
