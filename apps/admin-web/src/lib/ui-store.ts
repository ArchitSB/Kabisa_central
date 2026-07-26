import { create } from "zustand";

type UiState = {
  mobileNavOpen: boolean;
  previewRole: string;
  setMobileNavOpen: (open: boolean) => void;
  setPreviewRole: (role: string) => void;
};

export const useUiStore = create<UiState>((set) => ({
  mobileNavOpen: false,
  previewRole: "Super admin",
  setMobileNavOpen: (mobileNavOpen) => set({ mobileNavOpen }),
  setPreviewRole: (previewRole) => set({ previewRole }),
}));
