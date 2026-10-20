import {
  BadgePercent,
  Boxes,
  ChartNoAxesCombined,
  ClipboardList,
  ContactRound,
  LayoutDashboard,
  MessageSquareText,
  PackageSearch,
  Settings,
  ShieldCheck,
  Store,
  Tags,
  Truck,
  FileClock,
  UserRoundCog,
  Warehouse as WarehouseIcon,
  type LucideIcon,
} from "lucide-react";

type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  permission?: string;
};

export const navigation: Array<{ label: string; items: NavItem[] }> = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", href: "/", icon: LayoutDashboard }],
  },
  {
    label: "Operations",
    items: [
      { label: "Orders", href: "/orders", icon: ClipboardList, permission: "orders.view" },
      {
        label: "Products",
        href: "/products",
        icon: PackageSearch,
        permission: "products.view",
      },
      { label: "Inventory", href: "/inventory", icon: Boxes, permission: "inventory.view" },
      { label: "Customers", href: "/customers", icon: Store, permission: "customers.view" },
      {
        label: "Customer feedback",
        href: "/customers/feedback",
        icon: MessageSquareText,
        permission: "customer_feedback.view",
      },
      {
        label: "Delivery agents",
        href: "/delivery-agents",
        icon: Truck,
        permission: "delivery_agents.view",
      },
    ],
  },
  {
    label: "Storefront",
    items: [
      {
        label: "Storefront",
        href: "/storefront",
        icon: Store,
        permission: "storefront.view",
      },
    ],
  },
  {
    label: "Management",
    items: [
      {
        label: "Categories",
        href: "/categories",
        icon: Tags,
        permission: "categories.view",
      },
      { label: "Brands", href: "/brands", icon: ContactRound, permission: "brands.view" },
      {
        label: "Warehouses",
        href: "/warehouses",
        icon: WarehouseIcon,
        permission: "inventory.view",
      },
      {
        label: "Coupons",
        href: "/coupons",
        icon: BadgePercent,
        permission: "coupons.view",
      },
      {
        label: "Reports",
        href: "/reports",
        icon: ChartNoAxesCombined,
        permission: "reports.view",
      },
      {
        label: "Audit log",
        href: "/audit",
        icon: FileClock,
        permission: "audit.view",
      },
      {
        label: "Admin users",
        href: "/admin-users",
        icon: UserRoundCog,
        permission: "admin_users.view",
      },
      { label: "Roles", href: "/roles", icon: ShieldCheck, permission: "roles.view" },
      { label: "Settings", href: "/settings", icon: Settings, permission: "settings.view" },
    ],
  },
];
