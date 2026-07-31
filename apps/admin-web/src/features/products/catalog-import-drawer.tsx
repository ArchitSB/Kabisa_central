import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileWarning, Upload } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
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
import { FileUpload } from "@/components/ui/file-upload";
import { importCatalog } from "@/features/catalog/catalog-api";
import type { CatalogImportResult } from "@/features/catalog/types";
import { getApiErrorDetail } from "@/lib/api-errors";
import type { ColumnDef } from "@tanstack/react-table";

const previewColumns: ColumnDef<CatalogImportResult["preview"][number]>[] = [
  { accessorKey: "row", header: "Row" },
  { accessorKey: "sku", header: "SKU" },
  { accessorKey: "name", header: "Product" },
  { accessorKey: "action", header: "Action" },
];
const errorColumns: ColumnDef<CatalogImportResult["errors"][number]>[] = [
  { accessorKey: "row", header: "Row" },
  { accessorKey: "field", header: "Field" },
  { accessorKey: "detail", header: "Issue" },
];

export function CatalogImportDrawer({ trigger }: { trigger: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<CatalogImportResult | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ selectedFile, confirm }: { selectedFile: File; confirm: boolean }) =>
      importCatalog(selectedFile, confirm),
    onSuccess: async (data) => {
      setResult(data);
      if (data.committed) {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["products"] }),
          queryClient.invalidateQueries({ queryKey: ["inventory"] }),
        ]);
        toast.success("Catalog import committed", {
          description: `${data.created} created · ${data.updated} updated`,
        });
      }
    },
    onError: (error) =>
      toast.error("Catalog could not be validated", {
        description: getApiErrorDetail(error),
      }),
  });
  function changeOpen(next: boolean) {
    setOpen(next);
    if (!next) {
      setFile(null);
      setResult(null);
    }
  }
  return (
    <Drawer open={open} onOpenChange={changeOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent className="max-w-[820px]">
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Bulk catalog
          </p>
          <DrawerTitle>Import products from CSV</DrawerTitle>
          <DrawerDescription>
            Validate every row first. Nothing is written until you confirm a clean preview.
          </DrawerDescription>
        </DrawerHeader>
        <div className="flex-1 space-y-6 px-6 py-6">
          <FileUpload
            accept=".csv,text/csv"
            file={file}
            onFileChange={(next) => {
              setFile(next);
              setResult(null);
            }}
            label="Choose catalog CSV"
            hint="Use the exported template columns and UTF-8 encoding."
          />
          {result ? (
            <>
              <div
                className={`rounded-control border p-4 ${result.valid ? "border-success/20 bg-success-surface" : "border-danger/20 bg-danger-surface"}`}
              >
                <div className="flex items-start gap-3">
                  {result.valid ? (
                    <CheckCircle2
                      aria-hidden="true"
                      className="mt-0.5 size-5 shrink-0 text-success"
                    />
                  ) : (
                    <FileWarning
                      aria-hidden="true"
                      className="mt-0.5 size-5 shrink-0 text-danger"
                    />
                  )}
                  <div>
                    <p className="font-semibold">
                      {result.committed
                        ? "Import complete"
                        : result.valid
                          ? "Ready to import"
                          : "Validation needs attention"}
                    </p>
                    <p className="mt-1 text-sm text-secondary">
                      {result.valid_rows} of {result.total_rows} rows valid ·{" "}
                      {result.created} new · {result.updated} updates
                    </p>
                  </div>
                </div>
              </div>
              {result.errors.length ? (
                <div>
                  <h3 className="mb-3 font-semibold">Row errors</h3>
                  <DataTable
                    ariaLabel="Catalog import errors"
                    columns={errorColumns}
                    data={result.errors}
                    getRowId={(item) => `${item.row}-${item.field}`}
                    selectable={false}
                    pageSize={8}
                  />
                </div>
              ) : null}
              {result.preview.length ? (
                <div>
                  <h3 className="mb-3 font-semibold">Preview</h3>
                  <DataTable
                    ariaLabel="Catalog import preview"
                    columns={previewColumns}
                    data={result.preview}
                    getRowId={(item) => `${item.row}-${item.sku}`}
                    selectable={false}
                    pageSize={8}
                  />
                </div>
              ) : null}
            </>
          ) : null}
        </div>
        <DrawerFooter>
          <DrawerClose asChild>
            <Button type="button" variant="secondary">
              Close
            </Button>
          </DrawerClose>
          {result?.valid && !result.committed ? (
            <Button
              type="button"
              disabled={!file || mutation.isPending}
              onClick={() => file && mutation.mutate({ selectedFile: file, confirm: true })}
            >
              {mutation.isPending ? "Importing…" : "Confirm import"}
            </Button>
          ) : (
            <Button
              type="button"
              disabled={!file || mutation.isPending}
              onClick={() =>
                file && mutation.mutate({ selectedFile: file, confirm: false })
              }
            >
              <Upload aria-hidden="true" />
              {mutation.isPending ? "Validating…" : "Validate CSV"}
            </Button>
          )}
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}
