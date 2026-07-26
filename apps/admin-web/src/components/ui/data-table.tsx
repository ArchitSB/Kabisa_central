import { useEffect, useMemo, useState } from "react";
import {
  type ColumnDef,
  type RowData,
  type RowSelectionState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";

import { Checkbox } from "@/components/ui/checkbox";
import { Pagination } from "@/components/ui/pagination";
import { cn } from "@/lib/utils";

declare module "@tanstack/react-table" {
  // Generic parameters are required by TanStack's declaration-merging contract.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData extends RowData, TValue> {
    align?: "left" | "right";
    className?: string;
  }
}

type DataTableProps<TData> = {
  columns: ColumnDef<TData>[];
  data: TData[];
  ariaLabel: string;
  getRowId?: (row: TData) => string;
  pageSize?: number;
  onSelectionChange?: (selectedRows: TData[]) => void;
};

export function DataTable<TData>({
  columns,
  data,
  ariaLabel,
  getRowId,
  pageSize = 6,
  onSelectionChange,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  const selectionColumn = useMemo<ColumnDef<TData>>(
    () => ({
      id: "select",
      enableSorting: false,
      header: ({ table }) => (
        <Checkbox
          aria-label="Select all visible rows"
          checked={
            table.getIsAllPageRowsSelected()
              ? true
              : table.getIsSomePageRowsSelected()
                ? "indeterminate"
                : false
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(Boolean(value))}
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          aria-label={`Select row ${row.index + 1}`}
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(Boolean(value))}
        />
      ),
      size: 42,
    }),
    [],
  );

  const table = useReactTable({
    data,
    columns: [selectionColumn, ...columns],
    state: {
      sorting,
      rowSelection,
    },
    enableRowSelection: true,
    onSortingChange: setSorting,
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getRowId,
    initialState: {
      pagination: {
        pageSize,
      },
    },
  });

  useEffect(() => {
    onSelectionChange?.(table.getSelectedRowModel().flatRows.map((row) => row.original));
  }, [onSelectionChange, rowSelection, table]);

  return (
    <div>
      <div className="surface-card scrollbar-subtle overflow-x-auto">
        <table
          className="w-full min-w-[980px] border-collapse text-left"
          aria-label={ariaLabel}
        >
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-border bg-[#FBFCFB]">
                {headerGroup.headers.map((header) => {
                  const align = header.column.columnDef.meta?.align;
                  return (
                    <th
                      key={header.id}
                      scope="col"
                      className={cn(
                        "h-12 whitespace-nowrap px-4 text-[11px] font-bold uppercase tracking-[0.08em] text-secondary",
                        align === "right" && "text-right",
                        header.column.columnDef.meta?.className,
                      )}
                      style={{ width: header.getSize() }}
                    >
                      {header.isPlaceholder ? null : header.column.getCanSort() ? (
                        <button
                          type="button"
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-md py-1 transition-colors duration-micro hover:text-primary-800",
                            align === "right" && "ml-auto",
                          )}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {header.column.getIsSorted() === "asc" ? (
                            <ArrowUp aria-label="Sorted ascending" className="size-3" />
                          ) : header.column.getIsSorted() === "desc" ? (
                            <ArrowDown aria-label="Sorted descending" className="size-3" />
                          ) : (
                            <ChevronsUpDown
                              aria-hidden="true"
                              className="size-3 text-muted"
                            />
                          )}
                        </button>
                      ) : (
                        flexRender(header.column.columnDef.header, header.getContext())
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  data-state={row.getIsSelected() ? "selected" : undefined}
                  className="border-b border-border transition-colors duration-micro last:border-b-0 hover:bg-[var(--row-hover)] data-[state=selected]:bg-primary-50"
                >
                  {row.getVisibleCells().map((cell) => {
                    const align = cell.column.columnDef.meta?.align;
                    return (
                      <td
                        key={cell.id}
                        className={cn(
                          "h-[58px] whitespace-nowrap px-4 text-sm text-foreground",
                          align === "right" && "text-right",
                          cell.column.columnDef.meta?.className,
                        )}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    );
                  })}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={table.getAllColumns().length}
                  className="h-40 px-4 text-center text-sm text-secondary"
                >
                  No records match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <Pagination
        page={table.getState().pagination.pageIndex + 1}
        pageCount={table.getPageCount()}
        canPrevious={table.getCanPreviousPage()}
        canNext={table.getCanNextPage()}
        onPrevious={() => table.previousPage()}
        onNext={() => table.nextPage()}
      />
    </div>
  );
}
