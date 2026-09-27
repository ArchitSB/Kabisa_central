import { z } from "zod";

export type Session = { access_token: string; refresh_token: string };
export type CartLine = {
  product_id: string;
  quantity: number;
  unit_price: string | number | null;
};
export const quantitySchema = z.number().int().min(1).max(100000);
export const cartItemSchema = z
  .object({ product_id: z.string().uuid(), quantity: quantitySchema })
  .strict();
export const phoneSchema = z
  .string()
  .transform(normalizePhone)
  .refine(
    (v) => /^\+255[67]\d{8}$/.test(v),
    "Enter a valid Tanzanian mobile number.",
  );
export const passwordSchema = z
  .string()
  .min(8)
  .refine(
    (value) =>
      [...value].reduce(
        (bytes, char) =>
          bytes +
          (char.codePointAt(0)! > 0xffff
            ? 4
            : char.codePointAt(0)! > 0x7ff
              ? 3
              : char.codePointAt(0)! > 0x7f
                ? 2
                : 1),
        0,
      ) <= 72,
    "Password must not exceed 72 UTF-8 bytes.",
  );
export function normalizePhone(value: string): string {
  const cleaned = value.replace(/[\s()-]/g, "");
  return cleaned.startsWith("0")
    ? `+255${cleaned.slice(1)}`
    : cleaned.startsWith("255")
      ? `+${cleaned}`
      : cleaned;
}
export function minorUnits(value: string | number): number {
  const [whole, fraction = ""] = String(value).split(".");
  if (!/^\d+$/.test(whole) || !/^\d*$/.test(fraction))
    throw new Error("Invalid money value");
  return Number(whole) * 100 + Number((fraction + "00").slice(0, 2));
}
export function cartSummary(lines: CartLine[]) {
  return {
    quantity: lines.reduce((s, l) => s + l.quantity, 0),
    subtotal: lines.some((l) => l.unit_price === null)
      ? null
      : lines.reduce((s, l) => s + minorUnits(l.unit_price!) * l.quantity, 0) /
        100,
  };
}
export function formatMoney(
  value: string | number,
  currency: string,
  locale = "en-TZ",
): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(Number(value));
}
export const orderStages = [
  "PENDING",
  "APPROVED",
  "PENDING_DELIVERY",
  "DELIVERED",
] as const;
export function canCancelOrder(status: string): boolean {
  return status === "PENDING";
}
export function mergeCart(
  local: { product_id: string; quantity: number }[],
  remote: { product_id: string; quantity: number }[],
) {
  const merged = new Map<string, number>();
  for (const item of [...remote, ...local]) {
    const line = cartItemSchema.parse(item);
    merged.set(
      line.product_id,
      Math.min(100000, (merged.get(line.product_id) ?? 0) + line.quantity),
    );
  }
  return [...merged].map(([product_id, quantity]) => ({
    product_id,
    quantity,
  }));
}
export type QuickOrderLine = {
  line: number;
  query: string;
  quantity: number;
  error?: string;
};
export function parseQuickOrder(input: string): QuickOrderLine[] {
  const lines = input.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length > 100)
    throw new Error("Use up to 100 products per quick order.");
  return lines.map((raw, index) => {
    const match = raw
      .trim()
      .match(/^(.+?)(?:\s*[,;\t]\s*|\s+[x×]\s*|\s+)([+-]?\d+(?:\.\d+)?)$/i);
    const quantity = match ? Number(match[2]) : 1;
    return {
      line: index + 1,
      query: (match?.[1] ?? raw).trim(),
      quantity,
      ...(!quantitySchema.safeParse(quantity).success
        ? { error: "quantity" }
        : {}),
    };
  });
}

export { en } from "./en";
export { sw } from "./sw";
