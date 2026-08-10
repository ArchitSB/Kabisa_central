import { useMemo, useState } from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, GitBranch, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DataTable } from "@/components/ui/data-table";
import { SearchInput } from "@/components/ui/filter-bar";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { CategoryDrawer } from "@/features/categories/category-drawer";
import {
  deleteCategory,
  listCategories,
  reorderCategories,
  saveCategory,
} from "@/features/catalog/catalog-api";
import type { Category } from "@/features/catalog/types";
import { useHasPermission } from "@/features/auth/auth-store";
import { getApiErrorDetail } from "@/lib/api-errors";
import { useDebouncedValue } from "@/lib/use-debounced-value";

export function CategoriesPage() {
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState<Category | null>(null);
  const deferredSearch = useDebouncedValue(search.trim());
  const canCreate = useHasPermission("categories.create");
  const canEdit = useHasPermission("categories.edit");
  const canDelete = useHasPermission("categories.delete");
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["categories", deferredSearch],
    queryFn: () => listCategories(deferredSearch),
    placeholderData: keepPreviousData,
  });
  const remove = useMutation({
    mutationFn: deleteCategory,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["categories"] });
      setDeleting(null);
      toast.success("Category removed");
    },
    onError: (error) =>
      toast.error("Category could not be removed", {
        description: getApiErrorDetail(error),
      }),
  });
  const toggle = useMutation({
    mutationFn: (category: Category) =>
      saveCategory(
        {
          name: category.name,
          parent_id: category.parent_id,
          image_path: category.image_path,
          description: category.description,
          sort_order: category.sort_order,
          is_active: !category.is_active,
        },
        category.id,
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
    onError: (error) =>
      toast.error("Status could not be changed", { description: getApiErrorDetail(error) }),
  });
  const reorder = useMutation({
    mutationFn: async ({
      category,
      direction,
    }: {
      category: Category;
      direction: number;
    }) => {
      const items = query.data?.items ?? [];
      const target = items.find(
        (item) => item.sort_order === category.sort_order + direction,
      );
      return reorderCategories(
        target
          ? [
              { id: category.id, sort_order: target.sort_order },
              { id: target.id, sort_order: category.sort_order },
            ]
          : [{ id: category.id, sort_order: Math.max(0, category.sort_order + direction) }],
      );
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
    onError: (error) =>
      toast.error("Order could not be changed", { description: getApiErrorDetail(error) }),
  });
  const columns = useMemo<ColumnDef<Category>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Category",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-control bg-primary-50 text-primary-700">
              <GitBranch aria-hidden="true" className="size-4" />
            </span>
            <span>
              <span className="block font-semibold">{row.original.name}</span>
              <span className="block font-mono text-xs text-secondary">
                /{row.original.slug}
              </span>
            </span>
          </div>
        ),
      },
      {
        accessorFn: (item) => item.parent?.name,
        id: "parent",
        header: "Parent",
        cell: ({ row }) => (
          <span className="text-secondary">{row.original.parent?.name ?? "Top level"}</span>
        ),
      },
      {
        accessorKey: "sort_order",
        header: "Order",
        cell: ({ row }) => (
          <div className="flex items-center gap-1">
            <span className="numeric min-w-5 text-secondary">
              {row.original.sort_order}
            </span>
            {canEdit ? (
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 min-h-8"
                  aria-label={`Move ${row.original.name} up`}
                  disabled={row.original.sort_order === 0 || reorder.isPending}
                  onClick={() => reorder.mutate({ category: row.original, direction: -1 })}
                >
                  <ArrowUp aria-hidden="true" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 min-h-8"
                  aria-label={`Move ${row.original.name} down`}
                  disabled={reorder.isPending}
                  onClick={() => reorder.mutate({ category: row.original, direction: 1 })}
                >
                  <ArrowDown aria-hidden="true" />
                </Button>
              </>
            ) : null}
          </div>
        ),
      },
      {
        accessorKey: "is_active",
        header: "Status",
        cell: ({ row }) =>
          canEdit ? (
            <button
              type="button"
              className="inline-flex min-h-10 items-center rounded-full"
              aria-label={`Set ${row.original.name} ${row.original.is_active ? "inactive" : "active"}`}
              onClick={() => toggle.mutate(row.original)}
            >
              <StatusBadge
                label={row.original.is_active ? "Active" : "Inactive"}
                tone={row.original.is_active ? "success" : "neutral"}
              />
            </button>
          ) : (
            <StatusBadge
              label={row.original.is_active ? "Active" : "Inactive"}
              tone={row.original.is_active ? "success" : "neutral"}
            />
          ),
      },
      ...(canEdit || canDelete
        ? [
            {
              id: "actions",
              header: "Actions",
              enableSorting: false,
              meta: { align: "right" as const },
              cell: ({ row }: { row: { original: Category } }) => (
                <div className="flex justify-end gap-1">
                  {canEdit ? (
                    <CategoryDrawer
                      category={row.original}
                      trigger={
                        <Button variant="ghost" size="sm">
                          <Pencil aria-hidden="true" />
                          Edit
                        </Button>
                      }
                    />
                  ) : null}
                  {canDelete ? (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setDeleting(row.original)}
                    >
                      <Trash2 aria-hidden="true" />
                      Delete
                    </Button>
                  ) : null}
                </div>
              ),
            },
          ]
        : []),
    ],
    [canDelete, canEdit, reorder, toggle],
  );
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Catalog structure"
        title="Categories"
        subtitle="Organize products into a therapeutic hierarchy with controlled display order."
        actions={
          canCreate ? (
            <CategoryDrawer
              trigger={
                <Button>
                  <Plus aria-hidden="true" />
                  Add category
                </Button>
              }
            />
          ) : null
        }
      />
      <section className="surface-card flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full sm:max-w-md">
          <SearchInput
            value={search}
            onValueChange={setSearch}
            placeholder="Search categories"
            ariaLabel="Search categories"
          />
        </div>
        <span className="text-sm text-secondary">
          <strong className="numeric text-foreground">{query.data?.total ?? 0}</strong>{" "}
          therapeutic groups
        </span>
      </section>
      {query.isPending ? (
        <LoadingState label="Loading categories…" />
      ) : query.isError ? (
        <ErrorState
          title="Categories could not be loaded"
          onRetry={() => query.refetch()}
        />
      ) : (
        <DataTable
          ariaLabel="Categories"
          columns={columns}
          data={query.data.items}
          getRowId={(item) => item.id}
          selectable={false}
          pageSize={12}
        />
      )}
      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove category?"
        description={`This soft-deletes ${deleting?.name ?? "the category"}. Categories linked to products or child categories cannot be removed.`}
        confirmLabel="Remove category"
        destructive
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
      />
    </div>
  );
}
