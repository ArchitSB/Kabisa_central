import { useEffect, useRef, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { NavLink, useParams } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import {
  ArrowDown,
  ArrowUp,
  Download,
  ImagePlus,
  Pencil,
  Plus,
  Save,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { PageHeader } from "@/components/ui/page-header";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
  DrawerFooter,
} from "@/components/ui/drawer";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { useHasPermission } from "@/features/auth/auth-store";
import { apiClient } from "@/lib/api-client";
import { getApiErrorDetail } from "@/lib/api-errors";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { cn } from "@/lib/utils";

type Row = { id: string; sort_order: number; is_active: boolean; [key: string]: unknown };
type Kind =
  | "banners"
  | "collections"
  | "pages"
  | "faqs"
  | "announcements"
  | "testimonials"
  | "menus"
  | "settings"
  | "prescriptions";
type FormField = {
  key: string;
  label: string;
  type?: "textarea" | "image" | "select" | "rich";
  options?: string[];
  required?: boolean;
};
const kinds: Kind[] = [
  "banners",
  "collections",
  "pages",
  "faqs",
  "announcements",
  "testimonials",
  "menus",
  "settings",
  "prescriptions",
];
const labels: Record<Kind, string> = {
  banners: "Banners",
  collections: "Collections",
  pages: "Policies & pages",
  faqs: "FAQs",
  announcements: "Announcements",
  testimonials: "Testimonials",
  menus: "Navigation",
  settings: "Storefront settings",
  prescriptions: "Prescriptions",
};
const fields: Record<string, FormField[]> = {
  banners: [
    { key: "title", label: "Headline", required: true, type: "textarea" },
    { key: "subtitle", label: "Supporting text", type: "textarea" },
    { key: "image_path", label: "Desktop image", type: "image" },
    { key: "mobile_image_path", label: "Mobile image", type: "image" },
    { key: "link_label", label: "Button label" },
    { key: "link_url", label: "Link destination (e.g. /catalog)" },
    {
      key: "placement",
      label: "Placement",
      type: "select",
      options: ["HOME_HERO", "HOME_STRIP", "CATEGORY", "PROMO"],
    },
  ],
  collections: [
    { key: "title", label: "Collection title", required: true },
    { key: "slug", label: "URL slug", required: true },
    { key: "subtitle", label: "Description", type: "textarea" },
    {
      key: "mode",
      label: "Product selection",
      type: "select",
      options: ["MANUAL", "RULES"],
    },
  ],
  pages: [
    { key: "title", label: "Page title", required: true },
    { key: "slug", label: "URL slug", required: true },
    { key: "body", label: "Page content", type: "rich", required: true },
  ],
  faqs: [
    { key: "question", label: "Question", required: true },
    { key: "answer", label: "Answer", type: "textarea", required: true },
    { key: "category", label: "Topic" },
  ],
  announcements: [
    { key: "message", label: "Message", type: "textarea", required: true },
    { key: "type", label: "Tone", type: "select", options: ["info", "warning", "success"] },
  ],
  testimonials: [
    { key: "author", label: "Author", required: true },
    { key: "organisation", label: "Organisation", required: true },
    { key: "quote", label: "Quote", type: "textarea", required: true },
  ],
  menus: [
    { key: "label", label: "Link label", required: true },
    { key: "link_url", label: "Destination", required: true },
    { key: "placement", label: "Placement", type: "select", options: ["HEADER", "FOOTER"] },
  ],
};
const inputClass =
  "min-h-11 w-full rounded-control border border-border bg-surface px-3 py-2 text-sm text-foreground outline-none focus:border-primary-500 focus:ring-4 focus:ring-primary-500/15";
const human = (value: string) =>
  value.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());
function title(row: Row) {
  return String(
    row.title ||
      row.question ||
      row.message ||
      row.author ||
      row.label ||
      row.original_filename ||
      row.id,
  );
}
async function downloadExport(kind: string) {
  const response = await apiClient.get(`/storefront/${kind}/export`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `storefront-${kind}.xlsx`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function StorefrontPage() {
  const params = useParams();
  const kind = (kinds.includes(params.kind as Kind) ? params.kind : "banners") as Kind;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Customer experience"
        title="Storefront"
        subtitle="Shape the catalog experience, keep customers informed and manage your online store."
      />
      <nav className="flex flex-wrap gap-2" aria-label="Storefront modules">
        {kinds.map((key) => (
          <NavLink
            to={`/storefront/${key}`}
            key={key}
            className={({ isActive }) =>
              cn(
                "rounded-full border px-4 py-2 text-xs font-semibold transition-colors",
                isActive
                  ? "border-primary-700 bg-primary-700 text-white"
                  : "border-border bg-surface text-secondary hover:border-primary-300",
              )
            }
          >
            {labels[key]}
          </NavLink>
        ))}
      </nav>
      {kind === "settings" ? (
        <SettingsEditor />
      ) : kind === "prescriptions" ? (
        <Prescriptions />
      ) : (
        <ContentList key={kind} kind={kind} />
      )}
    </div>
  );
}
function ContentList({ kind }: { kind: Kind }) {
  const [search, setSearch] = useState("");
  const debounced = useDebouncedValue(search);
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Row | null>(null);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Row[]>([]);
  const [deleting, setDeleting] = useState<Row | null>(null);
  const [pending, setPending] = useState(false);
  const canEdit = useHasPermission("storefront.manage");
  const canDelete = useHasPermission("storefront.delete");
  const canExport = useHasPermission("storefront.export");
  const query = useQuery({
    queryKey: ["storefront", kind, debounced, page],
    queryFn: async () =>
      (
        await apiClient.get<{
          items: Row[];
          total: number;
          page: number;
          page_size: number;
        }>(`/storefront/${kind}`, {
          params: { search: debounced || undefined, page, page_size: 25 },
        })
      ).data,
  });
  async function change(action: () => Promise<unknown>) {
    setPending(true);
    try {
      await action();
      await query.refetch();
      toast.success("Storefront updated");
    } catch (e) {
      toast.error(getApiErrorDetail(e));
    } finally {
      setPending(false);
    }
  }
  const columns: ColumnDef<Row>[] = [
    {
      id: "title",
      header: labels[kind],
      cell: ({ row }) => (
        <div className="max-w-lg">
          <p className="line-clamp-2 font-semibold text-foreground">
            {title(row.original)}
          </p>
          <p className="mt-1 text-xs text-muted">
            {String(
              row.original.slug || row.original.placement || row.original.category || "",
            )}
          </p>
        </div>
      ),
    },
    {
      accessorKey: "sort_order",
      header: "Position",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <span className="mr-2">{row.original.sort_order}</span>
          {canEdit && (
            <>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Move earlier"
                disabled={row.original.sort_order <= 0 || pending}
                onClick={() =>
                  void change(() =>
                    apiClient.patch(`/storefront/${kind}/${row.original.id}`, {
                      sort_order: Math.max(0, row.original.sort_order - 1),
                    }),
                  )
                }
              >
                <ArrowUp />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Move later"
                disabled={pending}
                onClick={() =>
                  void change(() =>
                    apiClient.patch(`/storefront/${kind}/${row.original.id}`, {
                      sort_order: row.original.sort_order + 1,
                    }),
                  )
                }
              >
                <ArrowDown />
              </Button>
            </>
          )}
        </div>
      ),
    },
    {
      id: "status",
      header: "Publishing",
      cell: ({ row }) => (
        <button
          disabled={!canEdit || pending}
          onClick={() =>
            void change(() =>
              apiClient.patch(`/storefront/${kind}/${row.original.id}`, {
                is_active: !row.original.is_active,
              }),
            )
          }
          className={cn(
            "rounded-full px-3 py-1 text-xs font-semibold",
            row.original.is_active
              ? "bg-success-surface text-success"
              : "bg-neutral-surface text-secondary",
          )}
        >
          {row.original.is_active ? "Active" : "Draft"}
        </button>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <div className="flex gap-2">
          {canEdit && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setEditing(row.original);
                setOpen(true);
              }}
            >
              <Pencil />
              Edit
            </Button>
          )}
          {canDelete && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setDeleting(row.original)}
            >
              <Trash2 />
              Delete
            </Button>
          )}
        </div>
      ),
    },
  ];
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface p-4">
        <label className="min-w-[200px] flex-1 sm:max-w-sm">
          <span className="sr-only">Search content</span>
          <input
            className={inputClass}
            placeholder={`Search ${labels[kind].toLowerCase()}…`}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </label>
        <div className="flex gap-2">
          {canExport && (
            <Button
              variant="secondary"
              onClick={() =>
                void downloadExport(kind).catch((e) => toast.error(getApiErrorDetail(e)))
              }
            >
              <Download />
              Excel export
            </Button>
          )}
          {canEdit && (
            <Button
              onClick={() => {
                setEditing(null);
                setOpen(true);
              }}
            >
              <Plus />
              Add {kind === "faqs" ? "FAQ" : kind.replace(/s$/, "")}
            </Button>
          )}
        </div>
      </div>
      {selected.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-card border border-primary-200 bg-primary-50 p-3 text-sm">
          <span>{selected.length} selected</span>
          {canEdit &&
            ["activate", "deactivate"].map((action) => (
              <Button
                key={action}
                variant="secondary"
                size="sm"
                disabled={pending}
                onClick={() =>
                  void change(() =>
                    apiClient.post(`/storefront/${kind}/bulk`, {
                      ids: selected.map((r) => r.id),
                      action,
                    }),
                  )
                }
              >
                {human(action)}
              </Button>
            ))}
          {canDelete && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() =>
                setDeleting({
                  id: "bulk",
                  sort_order: 0,
                  is_active: false,
                  title: `${selected.length} selected items`,
                })
              }
            >
              Delete selected
            </Button>
          )}
        </div>
      )}
      {query.isLoading ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState
          title={getApiErrorDetail(query.error)}
          onRetry={() => query.refetch()}
        />
      ) : (
        <>
          <DataTable
            key={`${kind}-${page}-${debounced}`}
            columns={columns}
            data={query.data?.items || []}
            ariaLabel={labels[kind]}
            pageSize={25}
            showPagination={false}
            onSelectionChange={setSelected}
          />
          <div className="flex items-center justify-between text-xs text-secondary">
            <span>
              {query.data?.total || 0} records · Page {page}
            </span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page * 25 >= (query.data?.total || 0)}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
      <ContentDrawer
        key={editing?.id || `new-${open}`}
        kind={kind}
        row={editing}
        open={open}
        onClose={() => setOpen(false)}
        onSaved={() => {
          setOpen(false);
          void query.refetch();
        }}
      />
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(value) => !value && setDeleting(null)}
        title="Delete storefront content?"
        description={`${deleting ? title(deleting) : ""} will be removed from the storefront.`}
        destructive
        pending={pending}
        confirmLabel="Delete"
        onConfirm={() =>
          void change(async () => {
            if (deleting?.id === "bulk")
              await apiClient.post(`/storefront/${kind}/bulk`, {
                ids: selected.map((r) => r.id),
                action: "delete",
              });
            else await apiClient.delete(`/storefront/${kind}/${deleting?.id}`);
            setDeleting(null);
            setSelected([]);
          })
        }
      />
    </>
  );
}
function RichText({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  function wrap(before: string, after: string) {
    const input = ref.current;
    if (!input) return;
    const start = input.selectionStart,
      end = input.selectionEnd;
    onChange(
      value.slice(0, start) + before + value.slice(start, end) + after + value.slice(end),
    );
    input.focus();
  }
  return (
    <div className="overflow-hidden rounded-control border border-border">
      <div className="flex flex-wrap gap-2 border-b border-border bg-bg p-2">
        {[
          ["Bold", "<strong>", "</strong>"],
          ["Italic", "<em>", "</em>"],
          ["Heading", "<h2>", "</h2>"],
          ["Paragraph", "<p>", "</p>"],
          ["List", "<ul><li>", "</li></ul>"],
        ].map(([label, before, after]) => (
          <button
            key={label}
            type="button"
            className="rounded border border-border bg-surface px-2 py-1 text-xs"
            onClick={() => wrap(before, after)}
          >
            {label}
          </button>
        ))}
      </div>
      <textarea
        ref={ref}
        className={cn(inputClass, "min-h-[280px] rounded-none border-0")}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <p className="p-3 text-xs text-muted">
        Write plain paragraphs or use the formatting controls. Only safe formatting is
        rendered on the storefront.
      </p>
    </div>
  );
}
function ContentDrawer({
  kind,
  row,
  open,
  onClose,
  onSaved,
}: {
  kind: Kind;
  row: Row | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const initial = Object.fromEntries(
    (fields[kind] || []).map((field) => [
      field.key,
      row?.[field.key] ?? field.options?.[0] ?? "",
    ]),
  );
  const [form, setForm] = useState<Record<string, unknown>>({
    ...initial,
    sort_order: row?.sort_order || 0,
    is_active: row?.is_active ?? true,
    starts_at: row?.starts_at || "",
    ends_at: row?.ends_at || "",
    product_ids: row?.product_ids || [],
    rules: row?.rules || {},
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [productSearch, setProductSearch] = useState("");
  const productsQuery = useQuery({
    queryKey: ["storefront-products", productSearch],
    queryFn: async () =>
      (
        await apiClient.get<{ items: { id: string; name: string; sku: string }[] }>(
          "/products",
          { params: { search: productSearch || undefined, page_size: 100 } },
        )
      ).data,
    enabled: kind === "collections" && open,
  });
  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {
        ...form,
        starts_at: form.starts_at ? new Date(String(form.starts_at)).toISOString() : null,
        ends_at: form.ends_at ? new Date(String(form.ends_at)).toISOString() : null,
      };
      if (kind !== "collections") {
        delete payload.product_ids;
        delete payload.rules;
      }
      for (const field of fields[kind] || [])
        if (payload[field.key as keyof typeof payload] === "")
          Object.assign(payload, { [field.key]: null });
      if (row) await apiClient.patch(`/storefront/${kind}/${row.id}`, payload);
      else await apiClient.post(`/storefront/${kind}`, payload);
      toast.success("Content saved");
      onSaved();
    } catch (e) {
      setError(getApiErrorDetail(e));
    } finally {
      setSaving(false);
    }
  }
  const set = (key: string, value: unknown) =>
    setForm((previous) => ({ ...previous, [key]: value }));
  return (
    <Drawer open={open} onOpenChange={(v) => !v && onClose()}>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>
            {row ? "Edit" : "Create"} {labels[kind].toLowerCase()}
          </DrawerTitle>
          <DrawerDescription>
            Changes appear on the storefront immediately when active and within the
            schedule.
          </DrawerDescription>
        </DrawerHeader>
        <form onSubmit={submit} className="flex flex-1 flex-col">
          <div className="space-y-5 px-6 py-6">
            {(fields[kind] || []).map((field) => (
              <label key={field.key} className="block space-y-2 text-sm font-medium">
                <span>
                  {field.label}
                  {field.required ? " *" : ""}
                </span>
                {field.type === "select" ? (
                  <select
                    className={inputClass}
                    value={String(form[field.key] || "")}
                    onChange={(e) => set(field.key, e.target.value)}
                  >
                    {field.options?.map((option) => (
                      <option key={option} value={option}>
                        {human(option)}
                      </option>
                    ))}
                  </select>
                ) : field.type === "rich" ? (
                  <RichText
                    value={String(form[field.key] || "")}
                    onChange={(value) => set(field.key, value)}
                  />
                ) : field.type === "textarea" ? (
                  <textarea
                    rows={4}
                    className={inputClass}
                    value={String(form[field.key] || "")}
                    required={field.required}
                    onChange={(e) => set(field.key, e.target.value)}
                  />
                ) : (
                  <input
                    className={inputClass}
                    value={String(form[field.key] || "")}
                    required={field.required}
                    onChange={(e) => set(field.key, e.target.value)}
                  />
                )}{" "}
                {field.type === "image" && (
                  <span className="block">
                    <label className="inline-flex cursor-pointer items-center gap-2 rounded border border-border px-3 py-2 text-xs">
                      <ImagePlus size={15} />
                      Upload image
                      <input
                        className="sr-only"
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        onChange={async (e) => {
                          const file = e.target.files?.[0];
                          if (!file) return;
                          try {
                            const data = new FormData();
                            data.append("file", file);
                            const result = await apiClient.post<{ url: string }>(
                              "/storefront/images",
                              data,
                              { headers: { "Content-Type": "multipart/form-data" } },
                            );
                            set(field.key, result.data.url);
                          } catch (e) {
                            setError(getApiErrorDetail(e));
                          }
                        }}
                      />
                    </label>
                  </span>
                )}
              </label>
            ))}
            {kind === "collections" &&
              (form.mode === "MANUAL" ? (
                <div>
                  <label className="block text-sm font-medium">
                    Select products
                    <input
                      className={cn(inputClass, "mt-2")}
                      value={productSearch}
                      onChange={(e) => setProductSearch(e.target.value)}
                      placeholder="Search product name or SKU"
                    />
                  </label>
                  <div className="mt-3 max-h-64 overflow-auto rounded-control border border-border p-3">
                    {productsQuery.data?.items.map((product) => (
                      <label
                        key={product.id}
                        className="flex cursor-pointer items-center gap-3 border-b border-border py-3 text-xs"
                      >
                        <input
                          type="checkbox"
                          checked={(form.product_ids as string[]).includes(product.id)}
                          onChange={(e) =>
                            set(
                              "product_ids",
                              e.target.checked
                                ? [...(form.product_ids as string[]), product.id]
                                : (form.product_ids as string[]).filter(
                                    (id) => id !== product.id,
                                  ),
                            )
                          }
                        />
                        <span>
                          {product.name}
                          <small className="ml-2 text-muted">{product.sku}</small>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-4 rounded-card border border-border p-4">
                  <p className="text-sm font-semibold">Collection rules</p>
                  {["category", "brand", "product_type", "sort"].map((key) => (
                    <label key={key} className="block space-y-2 text-xs">
                      <span>
                        {human(key)}
                        {key === "category" || key === "brand" ? " (slug)" : ""}
                      </span>
                      <input
                        className={inputClass}
                        placeholder={key === "sort" ? "featured, newest, name" : ""}
                        value={String((form.rules as Record<string, string>)[key] || "")}
                        onChange={(e) => {
                          const rules = { ...(form.rules as Record<string, string>) };
                          if (e.target.value) rules[key] = e.target.value;
                          else delete rules[key];
                          set("rules", rules);
                        }}
                      />
                    </label>
                  ))}
                </div>
              ))}
            <label className="block space-y-2 text-sm">
              <span>Position</span>
              <input
                className={inputClass}
                type="number"
                min={0}
                value={Number(form.sort_order)}
                onChange={(e) => set("sort_order", Number(e.target.value))}
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              {["starts_at", "ends_at"].map((key) => (
                <label className="space-y-2 text-xs" key={key}>
                  <span>{human(key)}</span>
                  <input
                    className={inputClass}
                    type="datetime-local"
                    value={form[key] ? String(form[key]).slice(0, 16) : ""}
                    onChange={(e) => set(key, e.target.value)}
                  />
                </label>
              ))}
            </div>
            <label className="flex items-center gap-3 text-sm">
              <input
                type="checkbox"
                checked={!!form.is_active}
                onChange={(e) => set("is_active", e.target.checked)}
              />
              Active on storefront
            </label>
            {error && (
              <p
                className="rounded-control bg-danger-surface p-3 text-sm text-danger"
                role="alert"
              >
                {error}
              </p>
            )}
          </div>
          <DrawerFooter>
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button disabled={saving} type="submit">
              <Save />
              {saving ? "Saving…" : "Save content"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
const help: Record<string, string> = {
  guest_price_visibility: "Choose whether visitors see prices or need to sign in.",
  require_verification_to_order:
    "Keep enabled for licensed-buyer verification before checkout. Suspended and rejected accounts remain blocked.",
  min_order_value: "Minimum basket subtotal before delivery and tax.",
  delivery_fee_mode: "Use a fixed fee, region-specific fees, or free delivery.",
  free_delivery_threshold: "Set to 0 to disable the free-delivery threshold.",
  enable_reviews:
    "Reserved for future product reviews; testimonials are managed separately.",
  maintenance_mode:
    "Immediately pause browsing and checkout; account documents and support remain accessible.",
  notification_messages: "Order and verification messages used by the notification outbox.",
  trust_badges: "Publish only verified claims about your business.",
};
const groups = [
  {
    title: "Commerce & access",
    keys: [
      "guest_price_visibility",
      "unverified_price_visibility",
      "guest_price_tier",
      "min_order_value",
      "tax_rate",
      "low_stock_display_threshold",
      "enable_registration",
      "require_verification_to_order",
      "enable_wishlist",
      "enable_reviews",
    ],
  },
  {
    title: "Delivery",
    keys: [
      "delivery_fee_mode",
      "delivery_fee_value",
      "free_delivery_threshold",
      "delivery_zones",
    ],
  },
  {
    title: "Support & social",
    keys: [
      "support_phone",
      "support_whatsapp",
      "support_email",
      "business_hours",
      "social_links",
    ],
  },
  {
    title: "Homepage & trust",
    keys: [
      "home_eyebrow",
      "home_categories_title",
      "home_categories_subtitle",
      "home_featured_title",
      "home_featured_subtitle",
      "home_quick_title",
      "home_quick_body",
      "home_trust_title",
      "home_trust_body",
      "footer_description",
      "facility_count",
      "trust_badges",
    ],
  },
  { title: "Search & sharing", keys: ["seo_title", "seo_description", "seo_og_image"] },
  {
    title: "Status & messages",
    keys: [
      "maintenance_mode",
      "maintenance_message",
      "announcement_enabled",
      "verification_messages",
      "notification_messages",
    ],
  },
];
function SettingsEditor() {
  const canEdit = useHasPermission("storefront.manage");
  const query = useQuery({
    queryKey: ["storefront-settings"],
    queryFn: async () =>
      (await apiClient.get<{ values: Record<string, unknown> }>("/storefront/settings"))
        .data,
  });
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (query.data) setForm(query.data.values);
  }, [query.data]);
  async function save() {
    setSaving(true);
    try {
      await apiClient.patch("/storefront/settings", form);
      toast.success("Storefront settings saved");
      await query.refetch();
    } catch (e) {
      toast.error(getApiErrorDetail(e));
    } finally {
      setSaving(false);
    }
  }
  if (query.isLoading) return <LoadingState />;
  if (query.isError)
    return (
      <ErrorState title={getApiErrorDetail(query.error)} onRetry={() => query.refetch()} />
    );
  return (
    <div className="space-y-5">
      {groups.map((group) => (
        <section
          className="rounded-card border border-border bg-surface p-6"
          key={group.title}
        >
          <h2 className="mb-5 font-display text-2xl">{group.title}</h2>
          <div className="grid gap-6 md:grid-cols-2">
            {group.keys.map((key) => (
              <div
                key={key}
                className={typeof form[key] === "object" ? "md:col-span-2" : ""}
              >
                <ValueEditor
                  label={human(key)}
                  value={form[key]}
                  disabled={!canEdit}
                  onChange={(value) =>
                    setForm((previous) => ({ ...previous, [key]: value }))
                  }
                  options={
                    key.includes("price_visibility")
                      ? ["hidden", "login_to_see", "visible"]
                      : key === "delivery_fee_mode"
                        ? ["flat", "zone", "free"]
                        : key === "guest_price_tier"
                          ? ["COMMUNITY", "DLDM", "WHOLESALE"]
                          : undefined
                  }
                />
                {help[key] && (
                  <p className="mt-2 text-xs leading-5 text-muted">{help[key]}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}
      {canEdit && (
        <div className="sticky bottom-4 flex justify-end rounded-card border border-border bg-surface/95 p-4 shadow-card">
          <Button disabled={saving} onClick={() => void save()}>
            <Save />
            {saving ? "Saving…" : "Save storefront settings"}
          </Button>
        </div>
      )}
    </div>
  );
}
function ValueEditor({
  label,
  value,
  onChange,
  disabled = false,
  options,
}: {
  label: string;
  value: unknown;
  onChange: (value: unknown) => void;
  disabled?: boolean;
  options?: string[];
}) {
  const [newKey, setNewKey] = useState("");
  if (Array.isArray(value))
    return (
      <div className="space-y-3">
        <p className="text-sm font-semibold">{label}</p>
        {value.map((item, i) => (
          <div className="rounded-control border border-border p-4" key={i}>
            <ValueEditor
              label={`Item ${i + 1}`}
              value={item}
              onChange={(next) =>
                onChange(value.map((v, index) => (index === i ? next : v)))
              }
              disabled={disabled}
            />
            {!disabled && (
              <Button
                variant="destructive"
                size="sm"
                className="mt-3"
                onClick={() => onChange(value.filter((_, index) => index !== i))}
              >
                Remove
              </Button>
            )}
          </div>
        ))}
        {!disabled && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onChange([...value, { title: "", description: "" }])}
          >
            <Plus />
            Add item
          </Button>
        )}
      </div>
    );
  if (value && typeof value === "object") {
    const object = value as Record<string, unknown>;
    const editableKeys = ["Delivery zones", "Social links"].includes(label);
    return (
      <div className="space-y-4 rounded-card border border-border bg-bg/50 p-4">
        <p className="text-sm font-semibold">{label}</p>
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(object).map(([key, item]) => (
            <div key={key}>
              <ValueEditor
                label={human(key)}
                value={item}
                disabled={disabled}
                onChange={(next) => onChange({ ...object, [key]: next })}
              />
              {editableKeys && !disabled && (
                <button
                  className="mt-2 text-xs text-danger"
                  onClick={() => {
                    const next = { ...object };
                    delete next[key];
                    onChange(next);
                  }}
                >
                  Remove {key}
                </button>
              )}
            </div>
          ))}
        </div>
        {editableKeys && !disabled && (
          <div className="flex gap-2">
            <input
              className={inputClass}
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              placeholder={label === "Delivery zones" ? "Region name" : "Network name"}
              aria-label="New entry name"
            />
            <Button
              variant="secondary"
              disabled={!newKey.trim() || newKey in object}
              onClick={() => {
                onChange({
                  ...object,
                  [newKey.trim()]: label === "Delivery zones" ? { fee: 0, eta: "" } : "",
                });
                setNewKey("");
              }}
            >
              Add
            </Button>
          </div>
        )}
      </div>
    );
  }
  return (
    <label className="block space-y-2 text-sm font-medium">
      <span>{label}</span>
      {typeof value === "boolean" ? (
        <span className="flex min-h-11 items-center gap-3">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value}
            onChange={(e) => onChange(e.target.checked)}
          />
          <span className="text-sm font-normal text-secondary">
            {value ? "Enabled" : "Disabled"}
          </span>
        </span>
      ) : options ? (
        <select
          className={inputClass}
          value={String(value ?? "")}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
        >
          {options.map((option) => (
            <option value={option} key={option}>
              {human(option)}
            </option>
          ))}
        </select>
      ) : typeof value === "number" ? (
        <input
          className={inputClass}
          type="number"
          min={0}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      ) : (
        <textarea
          rows={String(value ?? "").length > 100 ? 3 : 1}
          className={inputClass}
          disabled={disabled}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </label>
  );
}
function Prescriptions() {
  const canEdit = useHasPermission("storefront.manage");
  const query = useQuery({
    queryKey: ["storefront-prescriptions"],
    queryFn: async () =>
      (await apiClient.get<{ items: Row[] }>("/storefront/prescriptions")).data,
  });
  if (query.isLoading) return <LoadingState />;
  if (query.isError)
    return (
      <ErrorState title={getApiErrorDetail(query.error)} onRetry={() => query.refetch()} />
    );
  return (
    <div className="space-y-4">
      {!query.data?.items.length && (
        <p className="rounded-card border border-border bg-surface p-10 text-center text-secondary">
          Customer purchase authorisations will appear here.
        </p>
      )}
      {query.data?.items.map((row) => (
        <div
          className="flex flex-wrap items-center gap-4 rounded-card border border-border bg-surface p-5"
          key={row.id}
        >
          <div className="min-w-0 flex-1">
            <p className="font-semibold">{String(row.original_filename)}</p>
            <p className="mt-1 text-xs text-muted">
              {String(row.status)} · Order {String(row.order_id || "Not placed yet")}
            </p>
          </div>
          <Button
            variant="secondary"
            onClick={async () => {
              try {
                const result = await apiClient.get(
                  `/storefront/prescriptions/${row.id}/download`,
                  { responseType: "blob" },
                );
                const url = URL.createObjectURL(result.data);
                const a = document.createElement("a");
                a.href = url;
                a.download = String(row.original_filename);
                a.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
              } catch (e) {
                toast.error(getApiErrorDetail(e));
              }
            }}
          >
            <Download />
            Download
          </Button>
          {canEdit &&
            ["APPROVED", "REJECTED"].map((status) => (
              <Button
                key={status}
                variant={status === "APPROVED" ? "primary" : "secondary"}
                onClick={async () => {
                  const notes = window.prompt("Review note (optional)");
                  if (notes === null) return;
                  try {
                    await apiClient.patch(`/storefront/prescriptions/${row.id}`, {
                      status,
                      notes: notes || null,
                    });
                    await query.refetch();
                  } catch (e) {
                    toast.error(getApiErrorDetail(e));
                  }
                }}
              >
                {status === "APPROVED" ? "Approve" : "Reject"}
              </Button>
            ))}
        </div>
      ))}
    </div>
  );
}
