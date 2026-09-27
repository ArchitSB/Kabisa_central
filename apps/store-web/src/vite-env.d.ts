/// <reference types="vite/client" />
interface Window {
  __kabisaHome?: {
    accessToken: string | null;
    promise: Promise<import("@kabisa/api-client").StoreHome | null>;
  };
}
