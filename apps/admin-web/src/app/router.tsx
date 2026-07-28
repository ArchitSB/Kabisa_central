import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/app/app-layout";
import { AuthGuard } from "@/features/auth/auth-guard";
import { PermissionGuard } from "@/features/auth/permission-guard";

const permissionRoutes = [
  ["/products", "products.view"],
  ["/inventory", "inventory.view"],
  ["/customers", "customers.view"],
  ["/delivery-agents", "delivery_agents.view"],
  ["/categories", "categories.view"],
  ["/brands", "brands.view"],
  ["/coupons", "coupons.view"],
  ["/reports", "reports.view"],
  ["/settings", "settings.view"],
] as const;

export const router = createBrowserRouter([
  {
    path: "/login",
    lazy: async () => {
      const { LoginPage } = await import("@/features/auth/login-page");
      return { Component: LoginPage };
    },
  },
  {
    element: <AuthGuard />,
    children: [
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
            element: <PermissionGuard permission="orders.view" />,
            children: [
              {
                path: "/orders",
                lazy: async () => {
                  const { OrdersPage } = await import("@/features/orders/orders-page");
                  return { Component: OrdersPage };
                },
              },
            ],
          },
          {
            element: <PermissionGuard permission="admin_users.view" />,
            children: [
              {
                path: "/admin-users",
                lazy: async () => {
                  const { AdminUsersPage } =
                    await import("@/features/admin-users/admin-users-page");
                  return { Component: AdminUsersPage };
                },
              },
            ],
          },
          {
            element: <PermissionGuard permission="roles.view" />,
            children: [
              {
                path: "/roles",
                lazy: async () => {
                  const { RolesPage } = await import("@/features/roles/roles-page");
                  return { Component: RolesPage };
                },
              },
            ],
          },
          ...permissionRoutes.map(([path, permission]) => ({
            element: <PermissionGuard permission={permission} />,
            children: [
              {
                path,
                lazy: async () => {
                  const { PlaceholderPage } =
                    await import("@/features/placeholder/placeholder-page");
                  return { Component: PlaceholderPage };
                },
              },
            ],
          })),
        ],
      },
    ],
  },
]);
