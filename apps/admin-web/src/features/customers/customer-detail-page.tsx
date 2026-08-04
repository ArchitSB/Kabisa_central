import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BadgeCheck,
  Ban,
  Check,
  CheckCircle2,
  ClipboardCheck,
  Download,
  FileQuestion,
  FileText,
  MapPin,
  MessageSquare,
  PackageOpen,
  Pencil,
  Plus,
  RotateCcw,
  ShieldCheck,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tabs, type TabItem } from "@/components/ui/tabs";
import { getCatalogSettings } from "@/features/catalog/catalog-api";
import { useHasPermission } from "@/features/auth/auth-store";
import { CustomerDrawer } from "@/features/customers/customer-drawer";
import {
  BusinessTypeBadge,
  CustomerStatusBadge,
  DocumentStatusBadge,
} from "@/features/customers/customer-ui";
import { documentTypeLabels } from "@/features/customers/customer-options";
import {
  AddressDrawer,
  DocumentUploadDrawer,
  FeedbackDrawer,
  TextPromptDialog,
} from "@/features/customers/customer-workspace-dialogs";
import {
  deleteCustomerAddress,
  deleteCustomerDocument,
  downloadCustomerDocument,
  getCustomer,
  reinstateCustomer,
  rejectCustomer,
  reviewCustomerDocument,
  setDefaultAddress,
  setFeedbackHandled,
  submitCustomer,
  suspendCustomer,
  verifyCustomer,
} from "@/features/customers/customers-api";
import type {
  CustomerAddress,
  CustomerDocument,
  CustomerStatus,
  DocumentStatus,
} from "@/features/customers/types";
import { getApiErrorDetail } from "@/lib/api-errors";
import { formatMoney } from "@/lib/utils";

const dateTimeFormatter = new Intl.DateTimeFormat("en-TZ", {
  dateStyle: "medium",
  timeStyle: "short",
});

type CustomerAction = "verify" | "reject" | "suspend" | "reinstate";

const actionCopy: Record<
  CustomerAction,
  {
    title: string;
    description: string;
    label: string;
    confirm: string;
    destructive?: boolean;
  }
> = {
  verify: {
    title: "Verify with an override?",
    description:
      "One or more standard documents are not approved. Explain the institutional or regulatory exception before continuing.",
    label: "Override justification",
    confirm: "Verify customer",
  },
  reject: {
    title: "Reject verification?",
    description: "State what the customer must correct before resubmitting.",
    label: "Rejection reason",
    confirm: "Reject customer",
    destructive: true,
  },
  suspend: {
    title: "Suspend this account?",
    description: "A suspended customer cannot place or approve new orders.",
    label: "Suspension reason",
    confirm: "Suspend customer",
    destructive: true,
  },
  reinstate: {
    title: "Reinstate this account?",
    description: "Record why the account is safe to return to verified status.",
    label: "Reinstatement note",
    confirm: "Reinstate customer",
  },
};

export function CustomerDetailPage() {
  const { customerId = "" } = useParams();
  const [action, setAction] = useState<CustomerAction | null>(null);
  const [rejectingDocument, setRejectingDocument] = useState<CustomerDocument | null>(null);
  const [deletingDocument, setDeletingDocument] = useState<CustomerDocument | null>(null);
  const [deletingAddress, setDeletingAddress] = useState<CustomerAddress | null>(null);
  const canEdit = useHasPermission("customers.edit");
  const canVerify = useHasPermission("customers.verify");
  const canReviewDocuments = useHasPermission("customer_docs.review");
  const canViewFeedback = useHasPermission("customer_feedback.view");
  const queryClient = useQueryClient();
  const customer = useQuery({
    queryKey: ["customer", customerId],
    queryFn: () => getCustomer(customerId),
    enabled: Boolean(customerId),
  });
  const settings = useQuery({
    queryKey: ["catalog-settings"],
    queryFn: getCatalogSettings,
  });
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["customer", customerId] }),
      queryClient.invalidateQueries({ queryKey: ["customers"] }),
      queryClient.invalidateQueries({ queryKey: ["customer-feedback"] }),
    ]);
  const statusMutation = useMutation({
    mutationFn: async ({
      type,
      note = "",
    }: {
      type: CustomerAction | "submit";
      note?: string;
    }) => {
      if (type === "submit") return submitCustomer(customerId);
      if (type === "verify") return verifyCustomer(customerId, note || null);
      if (type === "reject") return rejectCustomer(customerId, note);
      if (type === "suspend") return suspendCustomer(customerId, note);
      return reinstateCustomer(customerId, note);
    },
    onSuccess: async (saved) => {
      await refresh();
      setAction(null);
      toast.success(`Customer is now ${saved.status.toLowerCase().replace("_", " ")}`);
    },
    onError: (error) =>
      toast.error("Customer status could not be changed", {
        description: getApiErrorDetail(error),
      }),
  });
  const documentReview = useMutation({
    mutationFn: ({
      id,
      status,
      notes,
    }: {
      id: string;
      status: DocumentStatus;
      notes: string | null;
    }) => reviewCustomerDocument(id, status, notes),
    onSuccess: async () => {
      await refresh();
      setRejectingDocument(null);
      toast.success("Document review saved");
    },
    onError: (error) =>
      toast.error("Document review could not be saved", {
        description: getApiErrorDetail(error),
      }),
  });
  const documentDelete = useMutation({
    mutationFn: (id: string) => deleteCustomerDocument(id),
    onSuccess: async () => {
      await refresh();
      setDeletingDocument(null);
      toast.success("Document removed");
    },
    onError: (error) =>
      toast.error("Document could not be removed", {
        description: getApiErrorDetail(error),
      }),
  });
  const addressDefault = useMutation({
    mutationFn: (id: string) => setDefaultAddress(customerId, id),
    onSuccess: async () => {
      await refresh();
      toast.success("Default delivery address updated");
    },
    onError: (error) =>
      toast.error("Default address could not be changed", {
        description: getApiErrorDetail(error),
      }),
  });
  const addressDelete = useMutation({
    mutationFn: (id: string) => deleteCustomerAddress(customerId, id),
    onSuccess: async () => {
      await refresh();
      setDeletingAddress(null);
      toast.success("Address removed");
    },
    onError: (error) =>
      toast.error("Address could not be removed", {
        description: getApiErrorDetail(error),
      }),
  });
  const feedbackUpdate = useMutation({
    mutationFn: ({ id, handled }: { id: string; handled: boolean }) =>
      setFeedbackHandled(id, handled),
    onSuccess: async () => {
      await refresh();
      toast.success("Feedback status updated");
    },
    onError: (error) =>
      toast.error("Feedback could not be updated", {
        description: getApiErrorDetail(error),
      }),
  });

  if (customer.isPending) return <LoadingState label="Loading customer workspace…" />;
  if (customer.isError || !customer.data) {
    return (
      <ErrorState title="Customer could not be loaded" onRetry={() => customer.refetch()} />
    );
  }
  const item = customer.data;
  const readiness = item.verification_readiness;
  const activeAction = action ? actionCopy[action] : null;
  const currency = settings.data?.currency ?? "TZS";

  async function download(document: CustomerDocument) {
    try {
      await downloadCustomerDocument(document);
    } catch (error) {
      toast.error("Document could not be downloaded", {
        description: getApiErrorDetail(error),
      });
    }
  }

  const tabs: TabItem[] = [
    {
      value: "overview",
      label: "Overview",
      content: (
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="surface-card p-5 sm:p-6">
            <h2 className="font-display text-xl font-semibold">Business profile</h2>
            <dl className="mt-5 grid gap-5 sm:grid-cols-2">
              <Info label="Contact person" value={item.contact_person ?? "Not recorded"} />
              <Info label="Phone" value={item.phone} />
              <Info label="Email" value={item.email ?? "Not recorded"} />
              <Info label="Region" value={item.region ?? "Not recorded"} />
              <Info label="Registered address" value={item.physical_address} wide />
              <Info label="Referred by" value={item.referred_by ?? "Not recorded"} />
              <Info label="Payment terms" value={item.payment_terms} />
              <Info
                label="Credit limit"
                value={
                  item.credit_limit !== null
                    ? formatMoney(Number(item.credit_limit), currency)
                    : "Not configured"
                }
              />
            </dl>
            {item.rejection_reason ? (
              <div className="mt-6 rounded-control border border-danger/20 bg-danger-surface p-4">
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-danger">
                  Rejection reason
                </p>
                <p className="mt-1 text-sm text-danger">{item.rejection_reason}</p>
              </div>
            ) : null}
          </section>
          <section className="surface-card p-5 sm:p-6">
            <h2 className="font-display text-xl font-semibold">Status history</h2>
            <div className="mt-5 space-y-5">
              {item.status_history.map((history, index) => (
                <div key={history.id} className="relative flex gap-3">
                  {index < item.status_history.length - 1 ? (
                    <span className="absolute bottom-[-20px] left-[9px] top-5 w-px bg-border" />
                  ) : null}
                  <span className="mt-1.5 size-[19px] shrink-0 rounded-full border-4 border-primary-100 bg-primary-700" />
                  <span>
                    <span className="block text-sm font-semibold">
                      {statusLabel(history.to_status)}
                    </span>
                    <span className="mt-0.5 block text-xs text-secondary">
                      {dateTimeFormatter.format(new Date(history.created_at))}
                    </span>
                    {history.note ? (
                      <span className="mt-1 block text-sm leading-5 text-secondary">
                        {history.note}
                      </span>
                    ) : null}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>
      ),
    },
    {
      value: "documents",
      label: "Documents",
      count: item.documents.length,
      content: (
        <div className="space-y-5">
          <ReadinessCard readiness={readiness} />
          <div className="flex justify-end">
            {canEdit ? (
              <DocumentUploadDrawer
                customerId={item.id}
                trigger={
                  <Button>
                    <Upload aria-hidden="true" />
                    Upload document
                  </Button>
                }
              />
            ) : null}
          </div>
          {item.documents.length ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {item.documents.map((document) => (
                <article key={document.id} className="surface-card p-5">
                  <div className="flex items-start gap-3">
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-control bg-primary-50 text-primary-700">
                      <FileText aria-hidden="true" className="size-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold">
                        {documentTypeLabels[document.doc_type]}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-secondary">
                        {document.original_filename}
                      </p>
                    </div>
                    <DocumentStatusBadge status={document.status} />
                  </div>
                  {document.notes ? (
                    <p className="mt-4 rounded-control bg-[#FBFCFB] p-3 text-sm leading-5 text-secondary">
                      {document.notes}
                    </p>
                  ) : null}
                  <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => download(document)}
                    >
                      <Download aria-hidden="true" />
                      View / download
                    </Button>
                    {canReviewDocuments ? (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={documentReview.isPending}
                          onClick={() =>
                            documentReview.mutate({
                              id: document.id,
                              status: "APPROVED",
                              notes: null,
                            })
                          }
                        >
                          <Check aria-hidden="true" />
                          Approve
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => setRejectingDocument(document)}
                        >
                          <X aria-hidden="true" />
                          Reject
                        </Button>
                      </>
                    ) : null}
                    {canEdit ? (
                      <Button
                        variant="destructive"
                        size="sm"
                        aria-label={`Delete ${document.original_filename}`}
                        onClick={() => setDeletingDocument(document)}
                      >
                        <Trash2 aria-hidden="true" />
                      </Button>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={FileQuestion}
              title="No documents uploaded"
              description="Upload the customer’s TIN, TMDA, Pharmacy Council, and TBS evidence to begin verification."
            />
          )}
        </div>
      ),
    },
    {
      value: "addresses",
      label: "Addresses",
      count: item.addresses.length,
      content: (
        <div className="space-y-5">
          <div className="flex justify-end">
            {canEdit ? (
              <AddressDrawer
                customerId={item.id}
                trigger={
                  <Button>
                    <Plus aria-hidden="true" />
                    Add address
                  </Button>
                }
              />
            ) : null}
          </div>
          {item.addresses.length ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {item.addresses.map((address) => (
                <article key={address.id} className="surface-card p-5">
                  <div className="flex items-start gap-3">
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-control bg-primary-50 text-primary-700">
                      <MapPin aria-hidden="true" className="size-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold">{address.label}</h3>
                        {address.is_default ? (
                          <StatusBadge label="Default" tone="success" />
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-secondary">
                        {address.address}
                      </p>
                      <p className="mt-2 text-xs text-secondary">
                        {[address.region, address.contact_person, address.phone]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                    </div>
                  </div>
                  {canEdit ? (
                    <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
                      {!address.is_default ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={addressDefault.isPending}
                          onClick={() => addressDefault.mutate(address.id)}
                        >
                          <CheckCircle2 aria-hidden="true" />
                          Set default
                        </Button>
                      ) : null}
                      <AddressDrawer
                        customerId={item.id}
                        address={address}
                        trigger={
                          <Button variant="ghost" size="sm">
                            <Pencil aria-hidden="true" />
                            Edit
                          </Button>
                        }
                      />
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setDeletingAddress(address)}
                      >
                        <Trash2 aria-hidden="true" />
                        Remove
                      </Button>
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={MapPin}
              title="No delivery addresses"
              description="Add a delivery location; the first becomes the customer’s default."
            />
          )}
        </div>
      ),
    },
    ...(canViewFeedback
      ? [
          {
            value: "feedback",
            label: "Feedback",
            count: item.feedback.length,
            content: (
              <div className="space-y-5">
                <div className="flex justify-end">
                  <FeedbackDrawer
                    customerId={item.id}
                    trigger={
                      <Button>
                        <Plus aria-hidden="true" />
                        Log feedback
                      </Button>
                    }
                  />
                </div>
                {item.feedback.length ? (
                  <div className="space-y-3">
                    {item.feedback.map((feedback) => (
                      <article key={feedback.id} className="surface-card p-5">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="font-semibold">
                                {feedback.subject ?? "General feedback"}
                              </h3>
                              <StatusBadge
                                label={feedback.is_handled ? "Handled" : "Needs action"}
                                tone={feedback.is_handled ? "success" : "warning"}
                              />
                            </div>
                            <p className="mt-2 text-sm leading-6 text-secondary">
                              {feedback.message}
                            </p>
                            <p className="mt-2 text-xs text-muted">
                              {dateTimeFormatter.format(new Date(feedback.created_at))}
                            </p>
                          </div>
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={feedbackUpdate.isPending}
                            onClick={() =>
                              feedbackUpdate.mutate({
                                id: feedback.id,
                                handled: !feedback.is_handled,
                              })
                            }
                          >
                            {feedback.is_handled ? (
                              <RotateCcw aria-hidden="true" />
                            ) : (
                              <Check aria-hidden="true" />
                            )}
                            {feedback.is_handled ? "Reopen" : "Mark handled"}
                          </Button>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={MessageSquare}
                    title="No feedback logged"
                    description="Service notes and customer requests will appear here."
                  />
                )}
              </div>
            ),
          },
        ]
      : []),
    {
      value: "orders",
      label: "Orders",
      count: item.order_history.total,
      content: (
        <EmptyState
          icon={PackageOpen}
          title="Review orders in the order workspace"
          description="Order creation already enforces this customer's verification status and assigned price tier."
          action={
            <Button asChild variant="secondary">
              <Link to="/orders">Open orders</Link>
            </Button>
          }
        />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/customers">
          <ArrowLeft aria-hidden="true" />
          Back to customers
        </Link>
      </Button>
      <PageHeader
        eyebrow="Verification workspace"
        title={item.business_name}
        subtitle={`${item.price_tier.name} pricing · ${item.region ?? "Region not recorded"}`}
        actions={
          <>
            {canVerify && ["PENDING", "REJECTED"].includes(item.status) ? (
              <Button
                variant="outline"
                disabled={statusMutation.isPending}
                onClick={() => statusMutation.mutate({ type: "submit" })}
              >
                <ClipboardCheck aria-hidden="true" />
                Submit for review
              </Button>
            ) : null}
            {canVerify && item.status === "UNDER_REVIEW" ? (
              <>
                <Button variant="destructive" onClick={() => setAction("reject")}>
                  <X aria-hidden="true" />
                  Reject
                </Button>
                <Button
                  disabled={statusMutation.isPending}
                  onClick={() =>
                    readiness.ready
                      ? statusMutation.mutate({ type: "verify" })
                      : setAction("verify")
                  }
                >
                  <ShieldCheck aria-hidden="true" />
                  Verify
                </Button>
              </>
            ) : null}
            {canVerify && item.status === "VERIFIED" ? (
              <Button variant="destructive" onClick={() => setAction("suspend")}>
                <Ban aria-hidden="true" />
                Suspend
              </Button>
            ) : null}
            {canVerify && item.status === "SUSPENDED" ? (
              <Button onClick={() => setAction("reinstate")}>
                <RotateCcw aria-hidden="true" />
                Reinstate
              </Button>
            ) : null}
            {canEdit ? (
              <CustomerDrawer
                customer={item}
                trigger={
                  <Button variant="secondary">
                    <Pencil aria-hidden="true" />
                    Edit profile
                  </Button>
                }
              />
            ) : null}
          </>
        }
      />
      <section className="surface-card p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <BusinessTypeBadge type={item.business_type} />
            <CustomerStatusBadge status={item.status} />
            <StatusBadge label={item.price_tier.code} tone="info" />
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Summary
              label="Approved docs"
              value={`${readiness.approved_count}/${readiness.required_count}`}
            />
            <Summary label="Addresses" value={String(item.addresses.length)} />
            <Summary label="Payment" value={item.payment_terms} />
          </div>
        </div>
      </section>
      <section className="surface-card px-4 pb-5 sm:px-6 sm:pb-6">
        <Tabs items={tabs} defaultValue="overview" ariaLabel="Customer workspace" />
      </section>

      {action && activeAction ? (
        <TextPromptDialog
          open
          onOpenChange={(open) => !open && setAction(null)}
          title={activeAction.title}
          description={activeAction.description}
          label={activeAction.label}
          confirmLabel={activeAction.confirm}
          destructive={activeAction.destructive}
          pending={statusMutation.isPending}
          onConfirm={(note) => statusMutation.mutate({ type: action, note })}
        />
      ) : null}
      <TextPromptDialog
        open={Boolean(rejectingDocument)}
        onOpenChange={(open) => !open && setRejectingDocument(null)}
        title="Reject this document?"
        description="Explain what is invalid or needs replacement."
        label="Review notes"
        confirmLabel="Reject document"
        destructive
        pending={documentReview.isPending}
        onConfirm={(notes) =>
          rejectingDocument &&
          documentReview.mutate({
            id: rejectingDocument.id,
            status: "REJECTED",
            notes,
          })
        }
      />
      <ConfirmDialog
        open={Boolean(deletingDocument)}
        onOpenChange={(open) => !open && setDeletingDocument(null)}
        title="Remove this document?"
        description="Verified standard evidence is locked until the customer is suspended."
        confirmLabel="Remove document"
        destructive
        pending={documentDelete.isPending}
        onConfirm={() => deletingDocument && documentDelete.mutate(deletingDocument.id)}
      />
      <ConfirmDialog
        open={Boolean(deletingAddress)}
        onOpenChange={(open) => !open && setDeletingAddress(null)}
        title="Remove this address?"
        description="If this is the default, the oldest remaining address becomes the new default."
        confirmLabel="Remove address"
        destructive
        pending={addressDelete.isPending}
        onConfirm={() => deletingAddress && addressDelete.mutate(deletingAddress.id)}
      />
    </div>
  );
}

function ReadinessCard({
  readiness,
}: {
  readiness: {
    ready: boolean;
    approved_count: number;
    required_count: number;
    pending: CustomerDocument["doc_type"][];
    rejected: CustomerDocument["doc_type"][];
    missing: CustomerDocument["doc_type"][];
  };
}) {
  const outstanding = [
    ...readiness.missing.map((type) => `Missing ${documentTypeLabels[type]}`),
    ...readiness.pending.map((type) => `${documentTypeLabels[type]} pending`),
    ...readiness.rejected.map((type) => `${documentTypeLabels[type]} rejected`),
  ];
  return (
    <div
      className={`rounded-card border p-5 ${readiness.ready ? "border-success/20 bg-success-surface" : "border-warning/20 bg-warning-surface"}`}
    >
      <div className="flex items-start gap-3">
        {readiness.ready ? (
          <BadgeCheck aria-hidden="true" className="mt-0.5 size-6 shrink-0 text-success" />
        ) : (
          <FileQuestion
            aria-hidden="true"
            className="mt-0.5 size-6 shrink-0 text-warning"
          />
        )}
        <div>
          <p className="font-semibold">
            {readiness.approved_count}/{readiness.required_count} approved ·{" "}
            {readiness.ready ? "Ready to verify" : "Evidence incomplete"}
          </p>
          <p className="mt-1 text-sm leading-6 text-secondary">
            {readiness.ready
              ? "All four standard regulatory documents are approved."
              : outstanding.join(" · ")}
          </p>
        </div>
      </div>
    </div>
  );
}

function Info({
  label,
  value,
  wide = false,
}: {
  label: string;
  value: string;
  wide?: boolean;
}) {
  return (
    <div className={wide ? "sm:col-span-2" : undefined}>
      <dt className="text-xs font-semibold uppercase tracking-[0.07em] text-muted">
        {label}
      </dt>
      <dd className="mt-1 text-sm font-medium leading-6">{value}</dd>
    </div>
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-[105px] rounded-control border border-border bg-[#FBFCFB] px-4 py-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-muted">
        {label}
      </p>
      <p className="numeric mt-1 font-semibold">{value}</p>
    </div>
  );
}

function statusLabel(status: CustomerStatus) {
  return {
    PENDING: "Pending",
    UNDER_REVIEW: "Under review",
    VERIFIED: "Verified",
    REJECTED: "Rejected",
    SUSPENDED: "Suspended",
  }[status];
}
