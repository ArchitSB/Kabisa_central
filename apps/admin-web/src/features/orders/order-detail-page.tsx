import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import {
  ArrowLeft,
  CheckCircle2,
  CreditCard,
  Download,
  PackageCheck,
  Truck,
  XCircle,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { useHasPermission } from "@/features/auth/auth-store";
import { orderTone, paymentTone } from "@/features/orders/order-columns";
import {
  approveOrder,
  assignDelivery,
  completeDelivery,
  downloadDeliveryProof,
  dispatchDelivery,
  getOrder,
  listDeliveryAgents,
  recordPayment,
  setOrderStatus,
} from "@/features/orders/orders-api";
import {
  orderStatusLabels,
  paymentStatusLabels,
  type PaymentMethod,
} from "@/features/orders/orders.data";
import { getApiErrorDetail } from "@/lib/api-errors";
import { formatMoney } from "@/lib/utils";

export function OrderDetailPage() {
  const { orderId = "" } = useParams();
  const queryClient = useQueryClient();
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("CASH");
  const [provider, setProvider] = useState("");
  const [transactionRef, setTransactionRef] = useState("");
  const [agentId, setAgentId] = useState("");
  const [proof, setProof] = useState<File | null>(null);
  const [deliveryNotes, setDeliveryNotes] = useState("");
  const canApprove = useHasPermission("orders.approve");
  const canCancel = useHasPermission("orders.cancel");
  const canStatus = useHasPermission("orders.status");
  const canRecord = useHasPermission("payments.record");
  const canAssign = useHasPermission("deliveries.assign");
  const order = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => getOrder(orderId),
    enabled: Boolean(orderId),
  });
  const agents = useQuery({
    queryKey: ["delivery-agents", "active"],
    queryFn: () => listDeliveryAgents({ is_active: true }),
    enabled: canAssign,
  });

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["order", orderId] }),
      queryClient.invalidateQueries({ queryKey: ["orders"] }),
      queryClient.invalidateQueries({ queryKey: ["inventory"] }),
    ]);
  }
  const action = useMutation({
    mutationFn: async (target: "APPROVE" | "CANCELLED" | "FAILED" | "UNFOUND") =>
      target === "APPROVE"
        ? approveOrder(orderId)
        : setOrderStatus(orderId, target, `${target.toLowerCase()} by admin.`),
    onSuccess: async (saved) => {
      await refresh();
      toast.success(`Order ${orderStatusLabels[saved.status].toLowerCase()}`);
    },
    onError: (error) =>
      toast.error("Order status could not be changed", {
        description: getApiErrorDetail(error),
      }),
  });
  const payment = useMutation({
    mutationFn: () =>
      recordPayment(orderId, {
        amount: Number(paymentAmount),
        method: paymentMethod,
        provider: provider || null,
        transaction_ref: transactionRef || null,
        status: "COLLECTED",
      }),
    onSuccess: async () => {
      await refresh();
      setPaymentAmount("");
      setProvider("");
      setTransactionRef("");
      toast.success("Payment recorded");
    },
    onError: (error) =>
      toast.error("Payment could not be recorded", {
        description: getApiErrorDetail(error),
      }),
  });
  const delivery = useMutation({
    mutationFn: async (target: "ASSIGN" | "DISPATCH" | "DELIVER") => {
      if (target === "ASSIGN")
        return assignDelivery(orderId, agentId, deliveryNotes || null);
      if (target === "DISPATCH") return dispatchDelivery(orderId);
      if (!proof) throw new Error("Select a delivery proof file.");
      return completeDelivery(orderId, proof, deliveryNotes);
    },
    onSuccess: async (saved) => {
      await refresh();
      setProof(null);
      toast.success(
        saved.status === "DELIVERED" ? "Delivery completed" : "Delivery updated",
      );
    },
    onError: (error) =>
      toast.error("Delivery could not be updated", {
        description: getApiErrorDetail(error),
      }),
  });

  if (order.isPending) return <LoadingState label="Loading order…" />;
  if (order.isError || !order.data)
    return <ErrorState title="Order could not be loaded" onRetry={() => order.refetch()} />;
  const data = order.data;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Order operations"
        title={data.order_number}
        subtitle={`${data.customer_name} · ${data.warehouse_name} · ${data.price_tier_code} pricing`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="secondary">
              <Link to="/orders">
                <ArrowLeft aria-hidden="true" />
                Orders
              </Link>
            </Button>
            {data.status === "PENDING" && canApprove ? (
              <Button onClick={() => action.mutate("APPROVE")} disabled={action.isPending}>
                <CheckCircle2 aria-hidden="true" />
                Approve
              </Button>
            ) : null}
            {["PENDING", "APPROVED", "PENDING_DELIVERY"].includes(data.status) &&
            canCancel ? (
              <Button
                variant="destructive"
                onClick={() => action.mutate("CANCELLED")}
                disabled={action.isPending}
              >
                <XCircle aria-hidden="true" />
                Cancel
              </Button>
            ) : null}
            {["PENDING", "APPROVED", "PENDING_DELIVERY"].includes(data.status) &&
            canStatus ? (
              <Button
                variant="secondary"
                onClick={() => action.mutate("FAILED")}
                disabled={action.isPending}
              >
                Mark failed
              </Button>
            ) : null}
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Order status">
          <StatusBadge
            label={orderStatusLabels[data.status]}
            tone={orderTone[data.status]}
          />
        </Metric>
        <Metric label="Payment">
          <StatusBadge
            label={paymentStatusLabels[data.payment_status]}
            tone={paymentTone[data.payment_status]}
          />
        </Metric>
        <Metric label="Total">
          <strong className="numeric text-lg">
            {formatMoney(data.total_amount, data.currency)}
          </strong>
        </Metric>
        <Metric label="Balance due">
          <strong className="numeric text-lg">
            {formatMoney(data.balance_due, data.currency)}
          </strong>
        </Metric>
      </div>

      <section className="overflow-hidden rounded-card border border-border bg-surface shadow-card">
        <div className="border-b border-border px-5 py-4">
          <h2 className="font-display text-xl font-semibold">Items & FEFO allocations</h2>
        </div>
        <div className="scrollbar-subtle overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-background text-xs uppercase tracking-wide text-secondary">
              <tr>
                <th className="px-5 py-3">Product</th>
                <th className="px-4 py-3">Qty</th>
                <th className="px-4 py-3">Unit price</th>
                <th className="px-4 py-3">Line total</th>
                <th className="px-4 py-3">Allocation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.items.map((item) => (
                <tr key={item.id}>
                  <td className="px-5 py-4">
                    <strong>{item.product_name}</strong>
                    <span className="block font-mono text-xs text-secondary">
                      {item.product_sku}
                    </span>
                  </td>
                  <td className="numeric px-4 py-4">{item.quantity}</td>
                  <td className="numeric px-4 py-4">
                    {formatMoney(item.unit_price, data.currency)}
                  </td>
                  <td className="numeric px-4 py-4 font-semibold">
                    {formatMoney(item.line_total, data.currency)}
                  </td>
                  <td className="px-4 py-4">
                    {item.allocations.length ? (
                      <div className="space-y-1">
                        {item.allocations.map((allocation) => (
                          <p key={allocation.id} className="text-xs">
                            <span className="font-mono font-semibold">
                              {allocation.batch_number}
                            </span>{" "}
                            · {allocation.quantity} · exp{" "}
                            {format(new Date(allocation.expiry_date), "dd MMM yyyy")}
                          </p>
                        ))}
                      </div>
                    ) : (
                      <span className="text-secondary">
                        Not reserved · {item.on_hand} on-hand
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-card border border-border bg-surface p-5 shadow-card">
          <div className="mb-5 flex items-center gap-2">
            <CreditCard className="size-5 text-primary-700" aria-hidden="true" />
            <h2 className="font-display text-xl font-semibold">Payments</h2>
          </div>
          {canRecord && data.balance_due > 0 ? (
            <div className="mb-5 grid gap-3 rounded-card border border-border bg-background p-4 sm:grid-cols-2">
              <FormField label="Amount" htmlFor="payment-amount">
                <Input
                  id="payment-amount"
                  type="number"
                  min="0.01"
                  max={data.balance_due}
                  step="0.01"
                  value={paymentAmount}
                  onChange={(event) => setPaymentAmount(event.target.value)}
                />
              </FormField>
              <FormField label="Method" htmlFor="payment-method">
                <select
                  id="payment-method"
                  className="control-base w-full"
                  value={paymentMethod}
                  onChange={(event) =>
                    setPaymentMethod(event.target.value as PaymentMethod)
                  }
                >
                  <option value="CASH">Cash</option>
                  <option value="MOBILE_MONEY">Mobile money</option>
                  <option value="BANK_TRANSFER">Bank transfer</option>
                  <option value="OTHER">Other</option>
                </select>
              </FormField>
              {paymentMethod === "MOBILE_MONEY" ? (
                <FormField label="Provider" htmlFor="payment-provider">
                  <Input
                    id="payment-provider"
                    placeholder="M-Pesa, Airtel, Mixx…"
                    value={provider}
                    onChange={(event) => setProvider(event.target.value)}
                  />
                </FormField>
              ) : null}
              <FormField label="Transaction reference" htmlFor="payment-ref">
                <Input
                  id="payment-ref"
                  value={transactionRef}
                  onChange={(event) => setTransactionRef(event.target.value)}
                />
              </FormField>
              <div className="sm:col-span-2">
                <Button
                  disabled={!paymentAmount || payment.isPending}
                  onClick={() => payment.mutate()}
                >
                  {payment.isPending ? "Recording…" : "Record collected payment"}
                </Button>
              </div>
            </div>
          ) : null}
          {data.payments.length ? (
            <div className="space-y-3">
              {data.payments.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-4 border-b border-border pb-3"
                >
                  <div>
                    <p className="font-semibold">{item.method.replaceAll("_", " ")}</p>
                    <p className="text-xs text-secondary">
                      {format(
                        new Date(item.paid_at ?? item.created_at),
                        "dd MMM yyyy, HH:mm",
                      )}{" "}
                      {item.transaction_ref ? `· ${item.transaction_ref}` : ""}
                    </p>
                  </div>
                  <strong className="numeric">
                    {formatMoney(item.amount, data.currency)}
                  </strong>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={CreditCard}
              title="No payments recorded"
              description="Collected payments will appear here."
            />
          )}
        </section>

        <section className="rounded-card border border-border bg-surface p-5 shadow-card">
          <div className="mb-5 flex items-center gap-2">
            <Truck className="size-5 text-primary-700" aria-hidden="true" />
            <h2 className="font-display text-xl font-semibold">Delivery</h2>
          </div>
          {data.status === "APPROVED" && canAssign ? (
            <div className="space-y-3 rounded-card border border-border bg-background p-4">
              <FormField label="Active delivery agent" htmlFor="delivery-agent">
                <select
                  id="delivery-agent"
                  className="control-base w-full"
                  value={agentId}
                  onChange={(event) => setAgentId(event.target.value)}
                >
                  <option value="">Select agent</option>
                  {agents.data?.items.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name} · {agent.vehicle_type?.toLowerCase() ?? "vehicle n/a"}
                    </option>
                  ))}
                </select>
              </FormField>
              <Button
                disabled={!agentId || delivery.isPending}
                onClick={() => delivery.mutate("ASSIGN")}
              >
                <Truck aria-hidden="true" />
                Assign delivery
              </Button>
            </div>
          ) : null}
          {data.delivery ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold">{data.delivery.agent?.name ?? "No agent"}</p>
                  <p className="text-xs text-secondary">{data.delivery.agent?.phone}</p>
                </div>
                <StatusBadge
                  label={data.delivery.status.replaceAll("_", " ")}
                  tone={
                    data.delivery.status === "DELIVERED"
                      ? "success"
                      : data.delivery.status === "FAILED"
                        ? "danger"
                        : "info"
                  }
                />
              </div>
              {data.delivery.status === "ASSIGNED" && canStatus ? (
                <Button
                  onClick={() => delivery.mutate("DISPATCH")}
                  disabled={delivery.isPending}
                >
                  <Truck aria-hidden="true" />
                  Dispatch
                </Button>
              ) : null}
              {data.delivery.proof_path ? (
                <Button
                  variant="secondary"
                  onClick={() =>
                    downloadDeliveryProof(data.delivery!.id).catch((error) =>
                      toast.error("Delivery proof could not be opened", {
                        description: getApiErrorDetail(error),
                      }),
                    )
                  }
                >
                  <Download aria-hidden="true" />
                  View delivery proof
                </Button>
              ) : null}
              {["ASSIGNED", "OUT_FOR_DELIVERY"].includes(data.delivery.status) &&
              canStatus ? (
                <div className="space-y-3 border-t border-border pt-4">
                  <FormField label="Delivery proof" htmlFor="delivery-proof">
                    <Input
                      id="delivery-proof"
                      type="file"
                      accept="application/pdf,image/jpeg,image/png"
                      onChange={(event) => setProof(event.target.files?.[0] ?? null)}
                    />
                  </FormField>
                  <FormField label="Delivery notes" htmlFor="delivery-notes">
                    <Input
                      id="delivery-notes"
                      value={deliveryNotes}
                      onChange={(event) => setDeliveryNotes(event.target.value)}
                    />
                  </FormField>
                  <Button
                    disabled={!proof || delivery.isPending}
                    onClick={() => delivery.mutate("DELIVER")}
                  >
                    <PackageCheck aria-hidden="true" />
                    Mark delivered
                  </Button>
                </div>
              ) : null}
            </div>
          ) : data.status !== "APPROVED" ? (
            <EmptyState
              icon={Truck}
              title="No delivery assigned"
              description="Delivery becomes available after stock is approved and reserved."
            />
          ) : null}
        </section>
      </div>

      <section className="rounded-card border border-border bg-surface p-5 shadow-card">
        <h2 className="mb-5 font-display text-xl font-semibold">Status timeline</h2>
        <ol className="space-y-4">
          {data.history.map((entry, index) => (
            <li key={entry.id} className="relative flex gap-4">
              <span className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-800">
                {index + 1}
              </span>
              <div className="min-w-0 flex-1 border-b border-border pb-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <strong>{orderStatusLabels[entry.to_status]}</strong>
                  <time className="numeric text-xs text-secondary">
                    {format(new Date(entry.created_at), "dd MMM yyyy, HH:mm")}
                  </time>
                </div>
                <p className="mt-1 text-sm text-secondary">
                  {entry.note ?? "Status updated."}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function Metric({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-card border border-border bg-surface p-5 shadow-card">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-secondary">
        {label}
      </p>
      {children}
    </div>
  );
}
