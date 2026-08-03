import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/app/app-layout";
import { AuthGuard } from "@/features/auth/auth-guard";
import { PermissionGuard } from "@/features/auth/permission-guard";

const permissionRoutes = [["/settings", "settings.view"]] as const;

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
              {
                path: "/orders/:orderId",
                lazy: async () => {
                  const { OrderDetailPage } =
                    await import("@/features/orders/order-detail-page");
                  return { Component: OrderDetailPage };
                },
              },
            ],
          },
          {
            element: <PermissionGuard permission="delivery_agents.view" />,
            children: [
              {
                path: "/delivery-agents",
                lazy: async () => {
                  const { DeliveryAgentsPage } =
                    await import("@/features/orders/delivery-agents-page");
                  return { Component: DeliveryAgentsPage };
                },
              },
            ],
          },
          {
            element: <PermissionGuard permission="products.view" />,
            children: [
              {
                path: "/products",
                lazy: async () => {
                  const { ProductsPage } =
                    await import("@/features/products/products-page");
                  return { Component: ProductsPage };
                },
              },
              {
                path: "/products/:productId",
                lazy: async () => {
                  const { ProductDetailPage } =
                    await import("@/features/products/product-detail-page");
                  return { Component: ProductDetailPage };
                },
              },
            ],
          },
          {
            element: <PermissionGuard permission="inventory.view" />,
            children: [
              {
                path: "/inventory",
                lazy: async () => {
                  const { InventoryPage } =
                    await import("@/features/inventory/inventory-page");
                  return { Component: InventoryPage };
                },
              },
              {
                path: "/warehouses",
                lazy: async () => {
                  const { WarehousesPage } =
                    await import("@/features/warehouses/warehouses-page");
                  return { Component: WarehousesPage };
                },
              },
            ],
          },
          {
            element: <PermissionGuard permission="categories.view" />,
            children: [
              {
                path: "/categories",
                lazy: async () => {
                  const { CategoriesPage } =
                    await import("@/features/categories/categories-page");
                  return { Component: CategoriesPage };
                },
              },
            ],
          },
          {
            element: <PermissionGuard permission="brands.view" />,
            children: [
              {
                path: "/brands",
                lazy: async () => {
                  const { BrandsPage } = await import("@/features/brands/brands-page");
                  return { Component: BrandsPage };
                },
              },
            ],
          },
          {
            element: <PermissionGuard permission="customers.view" />,
            children: [
              {
                path: "/customers",
                lazy: async () => {
                  const { CustomersPage } =
                    await import("@/features/customers/customers-page");
                  return { Component: CustomersPage };
                },
              },
              {
                path: "/customers/:customerId",
                lazy: async () => {
                  const { CustomerDetailPage } =
                    await import("@/features/customers/customer-detail-page");
                  return { Component: CustomerDetailPage };
                },
              },
            ],
          },
          {
            element: <PermissionGuard permission="customer_feedback.view" />,
            children: [
              {
                path: "/customers/feedback",
                lazy: async () => {
                  const { CustomerFeedbackPage } =
                    await import("@/features/customers/customer-feedback-page");
                  return { Component: CustomerFeedbackPage };
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
          {
            element: <PermissionGuard permission="coupons.view" />,
            children: [
              {
                path: "/coupons",
                lazy: async () => {
                  const { CouponsPage } = await import("@/features/coupons/coupons-page");
                  return { Component: CouponsPage };
                },
              },
            ],
          },
          {
            element: <PermissionGuard permission="reports.view" />,
            children: [
              {
                path: "/reports",
                lazy: async () => {
                  const { ReportsPage } = await import("@/features/reporting/reports-page");
                  return { Component: ReportsPage };
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
