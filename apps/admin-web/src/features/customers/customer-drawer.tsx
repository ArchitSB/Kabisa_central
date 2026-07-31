import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
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
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { listPriceTiers } from "@/features/catalog/catalog-api";
import { businessTypeLabels } from "@/features/customers/customer-options";
import { saveCustomer } from "@/features/customers/customers-api";
import type {
  BusinessType,
  Customer,
  CustomerPayload,
  PaymentTerms,
} from "@/features/customers/types";
import { getApiErrorDetail } from "@/lib/api-errors";

const businessTypes = Object.keys(businessTypeLabels) as BusinessType[];
const schema = z
  .object({
    business_name: z.string().trim().min(2, "Enter the registered business name."),
    business_type: z.enum([
      "DLDM",
      "COMMUNITY_PHARMACY",
      "WHOLESALE",
      "HOSPITAL",
      "CLINIC",
      "GOVERNMENT",
      "NGO",
      "FBO",
    ]),
    price_tier_id: z.string().uuid("Select a price tier."),
    contact_person: z.string().trim(),
    email: z.string().trim().email("Enter a valid email.").or(z.literal("")),
    phone: z.string().trim().min(5, "Enter a contact number."),
    physical_address: z.string().trim().min(5, "Enter the legal address."),
    region: z.string().trim(),
    referred_by: z.string().trim(),
    payment_terms: z.enum(["CASH", "CREDIT"]),
    credit_limit: z.string().trim(),
  })
  .superRefine((values, context) => {
    if (
      values.payment_terms === "CREDIT" &&
      values.credit_limit &&
      Number(values.credit_limit) < 0
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["credit_limit"],
        message: "Credit limit cannot be negative.",
      });
    }
  });
type Values = z.infer<typeof schema>;

function suggestedTierCode(type: BusinessType) {
  if (type === "DLDM") return "DLDM";
  if (type === "COMMUNITY_PHARMACY") return "COMMUNITY";
  return "WHOLESALE";
}

export function CustomerDrawer({
  trigger,
  customer,
}: {
  trigger: React.ReactNode;
  customer?: Customer;
}) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const tiers = useQuery({
    queryKey: ["price-tiers"],
    queryFn: listPriceTiers,
    enabled: open,
  });
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      business_name: "",
      business_type: "COMMUNITY_PHARMACY",
      price_tier_id: "",
      contact_person: "",
      email: "",
      phone: "",
      physical_address: "",
      region: "",
      referred_by: "",
      payment_terms: "CASH",
      credit_limit: "",
    },
  });
  const paymentTerms = form.watch("payment_terms");
  const mutation = useMutation({
    mutationFn: (values: Values) => {
      const payload: CustomerPayload = {
        business_name: values.business_name,
        business_type: values.business_type,
        price_tier_id: values.price_tier_id,
        contact_person: values.contact_person || null,
        email: values.email || null,
        phone: values.phone,
        physical_address: values.physical_address,
        region: values.region || null,
        referred_by: values.referred_by || null,
        payment_terms: values.payment_terms,
        credit_limit:
          values.payment_terms === "CREDIT" && values.credit_limit
            ? Number(values.credit_limit)
            : null,
      };
      return saveCustomer(payload, customer?.id);
    },
    onSuccess: async (saved) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["customers"] }),
        queryClient.invalidateQueries({ queryKey: ["customer", saved.id] }),
      ]);
      toast.success(customer ? "Customer updated" : "Customer created", {
        description: saved.business_name,
      });
      setOpen(false);
    },
    onError: (error) =>
      toast.error("Customer could not be saved", {
        description: getApiErrorDetail(error),
      }),
  });

  useEffect(() => {
    if (!open) return;
    form.reset({
      business_name: customer?.business_name ?? "",
      business_type: customer?.business_type ?? "COMMUNITY_PHARMACY",
      price_tier_id: customer?.price_tier_id ?? "",
      contact_person: customer?.contact_person ?? "",
      email: customer?.email ?? "",
      phone: customer?.phone ?? "",
      physical_address: customer?.physical_address ?? "",
      region: customer?.region ?? "",
      referred_by: customer?.referred_by ?? "",
      payment_terms: customer?.payment_terms ?? "CASH",
      credit_limit: customer?.credit_limit ? String(customer.credit_limit) : "",
    });
  }, [customer, form, open]);

  useEffect(() => {
    if (!open || customer || form.getValues("price_tier_id") || !tiers.data) return;
    const type = form.getValues("business_type");
    const suggested = tiers.data.items.find(
      (tier) => tier.code === suggestedTierCode(type),
    );
    if (suggested) form.setValue("price_tier_id", suggested.id);
  }, [customer, form, open, tiers.data]);

  function setSuggestedTier(type: BusinessType) {
    const suggested = tiers.data?.items.find(
      (tier) => tier.code === suggestedTierCode(type),
    );
    if (suggested) {
      form.setValue("price_tier_id", suggested.id, { shouldValidate: true });
    }
  }

  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent className="max-w-[620px]">
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Customer account
          </p>
          <DrawerTitle>{customer ? "Edit customer" : "Create customer"}</DrawerTitle>
          <DrawerDescription>
            Capture the registered business, pricing tier, contacts, and dormant credit
            terms.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex flex-1 flex-col"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-6 px-6 py-6">
            <section>
              <h3 className="mb-4 text-sm font-bold text-foreground">Business details</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  label="Business name"
                  htmlFor="customer-business-name"
                  error={form.formState.errors.business_name?.message}
                  className="sm:col-span-2"
                >
                  <Input
                    id="customer-business-name"
                    autoFocus
                    aria-invalid={Boolean(form.formState.errors.business_name)}
                    {...form.register("business_name")}
                  />
                </FormField>
                <Controller
                  control={form.control}
                  name="business_type"
                  render={({ field }) => (
                    <FormField label="Business type" htmlFor="customer-business-type">
                      <select
                        id="customer-business-type"
                        className="control-base w-full"
                        value={field.value}
                        onChange={(event) => {
                          const value = event.target.value as BusinessType;
                          field.onChange(value);
                          setSuggestedTier(value);
                        }}
                      >
                        {businessTypes.map((type) => (
                          <option key={type} value={type}>
                            {businessTypeLabels[type]}
                          </option>
                        ))}
                      </select>
                    </FormField>
                  )}
                />
                <FormField
                  label="Price tier"
                  htmlFor="customer-price-tier"
                  hint="Suggested from business type; you can override it."
                  error={form.formState.errors.price_tier_id?.message}
                >
                  <select
                    id="customer-price-tier"
                    className="control-base w-full"
                    aria-invalid={Boolean(form.formState.errors.price_tier_id)}
                    {...form.register("price_tier_id")}
                  >
                    <option value="">Select tier</option>
                    {tiers.data?.items.map((tier) => (
                      <option key={tier.id} value={tier.id}>
                        {tier.name} ({tier.code})
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Contact person" htmlFor="customer-contact">
                  <Input id="customer-contact" {...form.register("contact_person")} />
                </FormField>
                <FormField
                  label="Phone"
                  htmlFor="customer-phone"
                  error={form.formState.errors.phone?.message}
                >
                  <Input
                    id="customer-phone"
                    type="tel"
                    aria-invalid={Boolean(form.formState.errors.phone)}
                    {...form.register("phone")}
                  />
                </FormField>
                <FormField
                  label="Email"
                  htmlFor="customer-email"
                  error={form.formState.errors.email?.message}
                >
                  <Input
                    id="customer-email"
                    type="email"
                    aria-invalid={Boolean(form.formState.errors.email)}
                    {...form.register("email")}
                  />
                </FormField>
                <FormField label="Region" htmlFor="customer-region">
                  <Input id="customer-region" {...form.register("region")} />
                </FormField>
                <FormField
                  label="Registered address"
                  htmlFor="customer-address"
                  error={form.formState.errors.physical_address?.message}
                  className="sm:col-span-2"
                >
                  <textarea
                    id="customer-address"
                    rows={3}
                    className="control-base h-auto w-full resize-y py-3"
                    aria-invalid={Boolean(form.formState.errors.physical_address)}
                    {...form.register("physical_address")}
                  />
                </FormField>
                <FormField
                  label="Referred by"
                  htmlFor="customer-referral"
                  className="sm:col-span-2"
                >
                  <Input id="customer-referral" {...form.register("referred_by")} />
                </FormField>
              </div>
            </section>
            <section className="border-t border-border pt-6">
              <h3 className="mb-4 text-sm font-bold text-foreground">Payment terms</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField label="Terms" htmlFor="customer-payment-terms">
                  <select
                    id="customer-payment-terms"
                    className="control-base w-full"
                    {...form.register("payment_terms")}
                  >
                    <option value="CASH">Cash</option>
                    <option value="CREDIT">Credit</option>
                  </select>
                </FormField>
                <FormField
                  label="Credit limit"
                  htmlFor="customer-credit-limit"
                  hint="Stored now; enforcement begins in Phase 4."
                  error={form.formState.errors.credit_limit?.message}
                >
                  <Input
                    id="customer-credit-limit"
                    type="number"
                    min="0"
                    step="0.01"
                    disabled={paymentTerms !== ("CREDIT" satisfies PaymentTerms)}
                    {...form.register("credit_limit")}
                  />
                </FormField>
              </div>
            </section>
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button type="submit" disabled={mutation.isPending || tiers.isPending}>
              {mutation.isPending ? "Saving…" : "Save customer"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
