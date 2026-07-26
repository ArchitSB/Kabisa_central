import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/app/app-layout";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      {
        path: "/",
        lazy: async () => {
          const { DashboardPage } = await import("@/features/dashboard/dashboard-page");
          return { Component: DashboardPage };
        },
      },
      {
        path: "/orders",
        lazy: async () => {
          const { OrdersPage } = await import("@/features/orders/orders-page");
          return { Component: OrdersPage };
        },
      },
      ...[
        "/products",
        "/inventory",
        "/customers",
        "/delivery-agents",
        "/categories",
        "/brands",
        "/coupons",
        "/reports",
        "/roles",
        "/settings",
      ].map((path) => ({
        path,
        lazy: async () => {
          const { PlaceholderPage } =
            await import("@/features/placeholder/placeholder-page");
          return { Component: PlaceholderPage };
        },
      })),
    ],
  },
]);
