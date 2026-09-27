/** Regenerate with: python scripts/export_openapi.py && pnpm --filter @kabisa/shared generate */
export type { paths, components, operations } from "./generated-api";
export type ApiListResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
