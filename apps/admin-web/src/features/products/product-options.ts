import type { ProductType } from "@/features/catalog/types";

export const productTypeLabels: Record<ProductType, string> = {
  PRESCRIPTION: "RX",
  OTC: "OTC",
  SPECIALTY: "Specialty",
  NUTRACEUTICAL: "Nutra",
  MEDICAL_DEVICE: "Device",
  CONSUMABLE: "Consumable",
};

export const productTypeOptions = Object.entries(productTypeLabels) as Array<
  [ProductType, string]
>;
