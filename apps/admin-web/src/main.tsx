import React from "react";
import { MotionConfig } from "motion/react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { Toaster } from "sonner";

import { router } from "@/app/router";
import { AppErrorBoundary } from "@/app/app-error-boundary";
import { queryClient } from "@/lib/query-client";
import "@/styles/globals.css";
import "@/styles/operations.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Kabisa admin root element was not found.");
}

const root = import.meta.hot?.data.root ?? ReactDOM.createRoot(rootElement);
if (import.meta.hot) import.meta.hot.data.root = root;
root.render(
  <React.StrictMode>
    <MotionConfig reducedMotion="user">
      <AppErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
          <Toaster
            position="top-right"
            richColors
            closeButton
            toastOptions={{
              classNames: {
                toast: "font-sans !rounded-card !border-border !shadow-drawer",
              },
            }}
          />
        </QueryClientProvider>
      </AppErrorBoundary>
    </MotionConfig>
  </React.StrictMode>,
);
