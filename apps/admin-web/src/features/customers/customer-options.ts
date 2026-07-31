import type { BusinessType, DocumentType } from "@/features/customers/types";

export const businessTypeLabels: Record<BusinessType, string> = {
  DLDM: "DLDM / ADDO",
  COMMUNITY_PHARMACY: "Community pharmacy",
  WHOLESALE: "Wholesaler",
  HOSPITAL: "Hospital",
  CLINIC: "Clinic",
  GOVERNMENT: "Government",
  NGO: "NGO",
  FBO: "FBO",
};

export const documentTypeLabels: Record<DocumentType, string> = {
  TIN: "TIN certificate",
  TMDA: "TMDA certificate",
  PHARMACY_COUNCIL: "Pharmacy Council",
  TBS: "TBS certificate",
  OTHER: "Other document",
};
