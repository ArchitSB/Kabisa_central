import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { saveDeliveryAgent, uploadDeliveryAgentProof } from "@/features/orders/orders-api";
import type { DeliveryAgent, VehicleType } from "@/features/orders/orders.data";
import { describeApiFailure } from "@/lib/api-errors";

const schema = z.object({
  name: z.string().trim().min(2, "Enter the agent's name."),
  phone: z.string().trim().min(5, "Enter a phone number."),
  email: z.string().trim().email("Enter a valid email.").or(z.literal("")),
  address: z.string().trim(),
  vehicle_type: z.enum(["MOTORCYCLE", "TRUCK", "VAN", "OTHER"]),
  is_active: z.boolean(),
});
type Values = z.infer<typeof schema>;

export function DeliveryAgentDrawer({
  trigger,
  agent,
}: {
  trigger: React.ReactNode;
  agent?: DeliveryAgent;
}) {
  const [open, setOpen] = useState(false);
  const [proof, setProof] = useState<File | null>(null);
  const [savedAgentId, setSavedAgentId] = useState<string | undefined>(agent?.id);
  const [proofError, setProofError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      phone: "",
      email: "",
      address: "",
      vehicle_type: "MOTORCYCLE",
      is_active: true,
    },
  });
  const save = useMutation({
    mutationFn: async (values: Values) => {
      const saved = await saveDeliveryAgent(
        { ...values, email: values.email || null, address: values.address || null },
        savedAgentId,
      );
      // Creation and proof upload are separate writes. Retain the successful ID
      // so retrying a failed upload updates this agent instead of creating another.
      setSavedAgentId(saved.id);
      if (proof) {
        try {
          await uploadDeliveryAgentProof(saved.id, proof);
        } catch (error) {
          return { proofError: describeApiFailure(error).message };
        }
      }
      return { proofError: null };
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["delivery-agents"] });
      setProofError(result.proofError);
      if (result.proofError) {
        toast.warning("Agent saved, but identity proof was not uploaded", {
          description: "Retry with the same file or choose a replacement below.",
        });
        return;
      }
      toast.success(agent ? "Delivery agent updated" : "Delivery agent created");
      setOpen(false);
      setProof(null);
    },
    onError: (error) =>
      toast.error("Delivery agent could not be saved", {
        description: describeApiFailure(error).message,
      }),
  });
  function changeOpen(nextOpen: boolean) {
    if (save.isPending) return;
    if (nextOpen) {
      form.reset({
        name: agent?.name ?? "",
        phone: agent?.phone ?? "",
        email: agent?.email ?? "",
        address: agent?.address ?? "",
        vehicle_type: agent?.vehicle_type ?? "MOTORCYCLE",
        is_active: agent?.is_active ?? true,
      });
      setSavedAgentId(agent?.id);
      setProof(null);
      setProofError(null);
    }
    setOpen(nextOpen);
  }
  return (
    <Drawer open={open} onOpenChange={changeOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent className="max-w-[540px]">
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Delivery fleet
          </p>
          <DrawerTitle>
            {agent ? "Edit delivery agent" : "Create delivery agent"}
          </DrawerTitle>
          <DrawerDescription>
            Manage contact, vehicle assignment, and operational availability.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex flex-1 flex-col"
          noValidate
          onSubmit={form.handleSubmit((values) => save.mutate(values))}
        >
          <fieldset
            disabled={save.isPending}
            className="grid gap-4 px-6 py-6 sm:grid-cols-2"
          >
            {proofError && (
              <div
                role="alert"
                className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 sm:col-span-2"
              >
                <p className="font-semibold">
                  Agent saved. Identity proof needs attention.
                </p>
                <p className="mt-1">{proofError}</p>
                <p className="mt-1">
                  Retry the upload below, choose another file, or close this form and upload
                  it later from Edit. Your agent details are already saved.
                </p>
              </div>
            )}
            <FormField
              label="Name"
              htmlFor="agent-name"
              error={form.formState.errors.name?.message}
              className="sm:col-span-2"
            >
              <Input id="agent-name" autoFocus {...form.register("name")} />
            </FormField>
            <FormField
              label="Phone"
              htmlFor="agent-phone"
              error={form.formState.errors.phone?.message}
            >
              <Input id="agent-phone" type="tel" {...form.register("phone")} />
            </FormField>
            <FormField
              label="Email"
              htmlFor="agent-email"
              error={form.formState.errors.email?.message}
            >
              <Input id="agent-email" type="email" {...form.register("email")} />
            </FormField>
            <FormField label="Vehicle" htmlFor="agent-vehicle">
              <select
                id="agent-vehicle"
                className="control-base w-full"
                {...form.register("vehicle_type")}
              >
                {(["MOTORCYCLE", "TRUCK", "VAN", "OTHER"] as VehicleType[]).map((type) => (
                  <option key={type} value={type}>
                    {type.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Status" htmlFor="agent-active">
              <select
                id="agent-active"
                className="control-base w-full"
                value={form.watch("is_active") ? "active" : "inactive"}
                onChange={(event) =>
                  form.setValue("is_active", event.target.value === "active")
                }
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </FormField>
            <FormField label="Address" htmlFor="agent-address" className="sm:col-span-2">
              <textarea
                id="agent-address"
                rows={3}
                className="control-base h-auto w-full py-3"
                {...form.register("address")}
              />
            </FormField>
            <FormField
              label="Identity proof"
              htmlFor="agent-id-proof"
              hint={
                agent?.id_proof_path
                  ? "A proof is already on file; select a file to replace it."
                  : "PDF, JPEG, or PNG."
              }
              className="sm:col-span-2"
            >
              <Input
                id="agent-id-proof"
                type="file"
                accept="application/pdf,image/jpeg,image/png"
                onChange={(event) => setProof(event.target.files?.[0] ?? null)}
              />
            </FormField>
          </fieldset>
          <DrawerFooter>
            <Button
              type="button"
              variant="secondary"
              disabled={save.isPending}
              onClick={() => changeOpen(false)}
            >
              {proofError ? "Close" : "Cancel"}
            </Button>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending
                ? "Saving…"
                : proofError
                  ? "Retry save & upload"
                  : "Save agent"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
