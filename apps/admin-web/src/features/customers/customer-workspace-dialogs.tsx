import { useEffect, useState } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
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
import { FileUpload } from "@/components/ui/file-upload";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { documentTypeLabels } from "@/features/customers/customer-options";
import {
  createFeedback,
  saveCustomerAddress,
  uploadCustomerDocument,
} from "@/features/customers/customers-api";
import type {
  CustomerAddress,
  CustomerAddressPayload,
  DocumentType,
} from "@/features/customers/types";
import { getApiErrorDetail } from "@/lib/api-errors";

export function TextPromptDialog({
  open,
  onOpenChange,
  title,
  description,
  label,
  confirmLabel,
  pending,
  destructive = false,
  required = true,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  label: string;
  confirmLabel: string;
  pending: boolean;
  destructive?: boolean;
  required?: boolean;
  onConfirm: (value: string) => void;
}) {
  const [value, setValue] = useState("");
  useEffect(() => {
    if (open) setValue("");
  }, [open]);
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-[70] bg-[#101619]/45 backdrop-blur-[2px] data-[state=closed]:animate-overlay-out data-[state=open]:animate-overlay-in" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-[71] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-surface p-6 shadow-drawer outline-none">
          <DialogPrimitive.Title className="font-display text-2xl font-semibold">
            {title}
          </DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-2 text-sm leading-6 text-secondary">
            {description}
          </DialogPrimitive.Description>
          <label
            htmlFor="workspace-action-note"
            className="mt-5 block text-sm font-semibold"
          >
            {label}
          </label>
          <textarea
            id="workspace-action-note"
            autoFocus
            rows={4}
            className="control-base mt-2 h-auto w-full resize-y py-3"
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <DialogPrimitive.Close asChild>
              <Button type="button" variant="secondary" disabled={pending}>
                Cancel
              </Button>
            </DialogPrimitive.Close>
            <Button
              type="button"
              variant={destructive ? "destructive" : "primary"}
              disabled={pending || (required && value.trim().length < 3)}
              onClick={() => onConfirm(value.trim())}
            >
              {pending ? "Working…" : confirmLabel}
            </Button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

const addressSchema = z.object({
  label: z.string().trim().min(1, "Enter an address label."),
  address: z.string().trim().min(5, "Enter the delivery address."),
  region: z.string().trim(),
  contact_person: z.string().trim(),
  phone: z.string().trim(),
  is_default: z.boolean(),
});
type AddressValues = z.infer<typeof addressSchema>;

export function AddressDrawer({
  customerId,
  address,
  trigger,
}: {
  customerId: string;
  address?: CustomerAddress;
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const form = useForm<AddressValues>({
    resolver: zodResolver(addressSchema),
    defaultValues: {
      label: "",
      address: "",
      region: "",
      contact_person: "",
      phone: "",
      is_default: false,
    },
  });
  const mutation = useMutation({
    mutationFn: (values: AddressValues) => {
      const payload: CustomerAddressPayload = {
        label: values.label,
        address: values.address,
        region: values.region || null,
        contact_person: values.contact_person || null,
        phone: values.phone || null,
        is_default: values.is_default,
      };
      return saveCustomerAddress(customerId, payload, address?.id);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["customer", customerId] });
      toast.success(address ? "Address updated" : "Address added");
      setOpen(false);
    },
    onError: (error) =>
      toast.error("Address could not be saved", {
        description: getApiErrorDetail(error),
      }),
  });
  useEffect(() => {
    if (!open) return;
    form.reset({
      label: address?.label ?? "",
      address: address?.address ?? "",
      region: address?.region ?? "",
      contact_person: address?.contact_person ?? "",
      phone: address?.phone ?? "",
      is_default: address?.is_default ?? false,
    });
  }, [address, form, open]);
  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>
            {address ? "Edit delivery address" : "Add delivery address"}
          </DrawerTitle>
          <DrawerDescription>
            Keep legal registration on the profile and delivery destinations here.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex flex-1 flex-col"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-5 px-6 py-6">
            <FormField
              label="Label"
              htmlFor="delivery-label"
              error={form.formState.errors.label?.message}
            >
              <Input id="delivery-label" autoFocus {...form.register("label")} />
            </FormField>
            <FormField
              label="Address"
              htmlFor="delivery-address"
              error={form.formState.errors.address?.message}
            >
              <textarea
                id="delivery-address"
                rows={4}
                className="control-base h-auto w-full resize-y py-3"
                {...form.register("address")}
              />
            </FormField>
            <FormField label="Region" htmlFor="delivery-region">
              <Input id="delivery-region" {...form.register("region")} />
            </FormField>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Contact person" htmlFor="delivery-contact">
                <Input id="delivery-contact" {...form.register("contact_person")} />
              </FormField>
              <FormField label="Phone" htmlFor="delivery-phone">
                <Input id="delivery-phone" type="tel" {...form.register("phone")} />
              </FormField>
            </div>
            <Controller
              control={form.control}
              name="is_default"
              render={({ field }) => (
                <label className="flex items-start gap-3 rounded-control border border-border bg-[#FBFCFB] p-4">
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={(value) => field.onChange(Boolean(value))}
                  />
                  <span>
                    <span className="block text-sm font-semibold">
                      Default delivery address
                    </span>
                    <span className="mt-0.5 block text-xs text-secondary">
                      Setting this unsets the previous default.
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
              {mutation.isPending ? "Saving…" : "Save address"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}

export function DocumentUploadDrawer({
  customerId,
  trigger,
}: {
  customerId: string;
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [documentType, setDocumentType] = useState<DocumentType>("TIN");
  const [file, setFile] = useState<File | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Choose a document first.");
      return uploadCustomerDocument(customerId, documentType, file);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["customer", customerId] });
      toast.success("Document uploaded for review");
      setFile(null);
      setOpen(false);
    },
    onError: (error) =>
      toast.error("Document could not be uploaded", {
        description: getApiErrorDetail(error),
      }),
  });
  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>Upload regulatory document</DrawerTitle>
          <DrawerDescription>
            PDF, JPEG, or PNG up to 10 MB. Files remain behind administrator authentication.
          </DrawerDescription>
        </DrawerHeader>
        <div className="flex flex-1 flex-col">
          <div className="space-y-5 px-6 py-6">
            <FormField label="Document type" htmlFor="customer-document-type">
              <select
                id="customer-document-type"
                className="control-base w-full"
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value as DocumentType)}
              >
                {(Object.keys(documentTypeLabels) as DocumentType[]).map((type) => (
                  <option key={type} value={type}>
                    {documentTypeLabels[type]}
                  </option>
                ))}
              </select>
            </FormField>
            <FileUpload
              accept="application/pdf,image/jpeg,image/png"
              file={file}
              onFileChange={setFile}
              label="Choose certificate"
              hint="PDF, JPEG, or PNG · maximum 10 MB"
            />
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button
              type="button"
              disabled={!file || mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              {mutation.isPending ? "Uploading…" : "Upload document"}
            </Button>
          </DrawerFooter>
        </div>
      </DrawerContent>
    </Drawer>
  );
}

const feedbackSchema = z.object({
  subject: z.string().trim().max(200),
  message: z.string().trim().min(3, "Enter the feedback or follow-up note."),
});
type FeedbackValues = z.infer<typeof feedbackSchema>;

export function FeedbackDrawer({
  customerId,
  trigger,
}: {
  customerId: string;
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const form = useForm<FeedbackValues>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: { subject: "", message: "" },
  });
  const mutation = useMutation({
    mutationFn: (values: FeedbackValues) =>
      createFeedback(customerId, {
        subject: values.subject || null,
        message: values.message,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["customer", customerId] }),
        queryClient.invalidateQueries({ queryKey: ["customer-feedback"] }),
      ]);
      form.reset();
      setOpen(false);
      toast.success("Feedback entry logged");
    },
    onError: (error) =>
      toast.error("Feedback could not be logged", {
        description: getApiErrorDetail(error),
      }),
  });
  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>Log customer feedback</DrawerTitle>
          <DrawerDescription>
            Record service feedback, customer requests, or an internal follow-up.
          </DrawerDescription>
        </DrawerHeader>
        <form
          className="flex flex-1 flex-col"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-5 px-6 py-6">
            <FormField label="Subject" htmlFor="feedback-subject">
              <Input id="feedback-subject" autoFocus {...form.register("subject")} />
            </FormField>
            <FormField
              label="Message"
              htmlFor="feedback-message"
              error={form.formState.errors.message?.message}
            >
              <textarea
                id="feedback-message"
                rows={6}
                className="control-base h-auto w-full resize-y py-3"
                {...form.register("message")}
              />
            </FormField>
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : "Log feedback"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
