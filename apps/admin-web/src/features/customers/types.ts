import type { PriceTier } from "@/features/catalog/types";

export type BusinessType =
  | "DLDM"
  | "COMMUNITY_PHARMACY"
  | "WHOLESALE"
  | "HOSPITAL"
  | "CLINIC"
  | "GOVERNMENT"
  | "NGO"
  | "FBO";
export type CustomerStatus =
  "PENDING" | "UNDER_REVIEW" | "VERIFIED" | "REJECTED" | "SUSPENDED";
export type PaymentTerms = "CASH" | "CREDIT";
export type DocumentType = "TIN" | "TMDA" | "PHARMACY_COUNCIL" | "TBS" | "OTHER";
export type DocumentStatus = "PENDING" | "APPROVED" | "REJECTED";

export type AuditFields = {
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
};

export type Customer = AuditFields & {
  id: string;
  business_name: string;
  business_type: BusinessType;
  price_tier_id: string;
  price_tier: PriceTier;
  contact_person: string | null;
  email: string | null;
  phone: string;
  physical_address: string;
  region: string | null;
  referred_by: string | null;
  status: CustomerStatus;
  payment_terms: PaymentTerms;
  credit_limit: number | null;
  verified_by: string | null;
  verified_at: string | null;
  rejection_reason: string | null;
  deleted_at: string | null;
};

export type CustomerPayload = Pick<
  Customer,
  | "business_name"
  | "business_type"
  | "price_tier_id"
  | "contact_person"
  | "email"
  | "phone"
  | "physical_address"
  | "region"
  | "referred_by"
  | "payment_terms"
  | "credit_limit"
>;

export type CustomerDocument = AuditFields & {
  id: string;
  customer_id: string;
  doc_type: DocumentType;
  original_filename: string;
  mime_type: string | null;
  status: DocumentStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  notes: string | null;
  download_url: string;
};

export type CustomerAddress = AuditFields & {
  id: string;
  customer_id: string;
  label: string;
  address: string;
  region: string | null;
  contact_person: string | null;
  phone: string | null;
  is_default: boolean;
  deleted_at: string | null;
};

export type CustomerAddressPayload = Pick<
  CustomerAddress,
  "label" | "address" | "region" | "contact_person" | "phone" | "is_default"
>;

export type CustomerFeedback = AuditFields & {
  id: string;
  customer_id: string | null;
  customer: { id: string; business_name: string } | null;
  subject: string | null;
  message: string;
  is_handled: boolean;
  handled_by: string | null;
  handled_at: string | null;
};

export type VerificationReadiness = {
  required: DocumentType[];
  approved: DocumentType[];
  pending: DocumentType[];
  rejected: DocumentType[];
  missing: DocumentType[];
  approved_count: number;
  required_count: number;
  ready: boolean;
};

export type StatusHistory = AuditFields & {
  id: string;
  customer_id: string;
  from_status: CustomerStatus | null;
  to_status: CustomerStatus;
  note: string | null;
};

export type CustomerDetail = Customer & {
  documents: CustomerDocument[];
  addresses: CustomerAddress[];
  feedback: CustomerFeedback[];
  status_history: StatusHistory[];
  verification_readiness: VerificationReadiness;
  order_history: { available: boolean; total: number; items: Record<string, unknown>[] };
};
