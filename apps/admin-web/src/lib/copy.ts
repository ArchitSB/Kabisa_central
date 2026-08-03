export const copy = {
  brand: {
    name: "Kabisa",
    product: "Admin",
    section: "ADMIN",
  },
  topbar: {
    preview: "Secure workspace",
    roleLabel: "Dev · Viewing as",
    menu: "Open navigation",
  },
  dashboard: {
    eyebrow: "Sunday, 26 July",
    title: "Operations overview",
    subtitle:
      "A clear view of orders, sales, inventory health, and customers across Kabisa.",
    actions: {
      report: "Download report",
      order: "Create order",
    },
    salesTitle: "Sales pulse",
    salesSubtitle: "Committed gross sales from approved and fulfilled orders.",
    watchlistTitle: "Inventory watchlist",
    watchlistSubtitle: "Items that need the inventory team’s attention.",
    recentTitle: "Recent orders",
    recentSubtitle: "The latest orders across the active fulfilment workflow.",
  },
  orders: {
    eyebrow: "Order management",
    title: "Orders",
    subtitle: "Review incoming demand, coordinate fulfilment, and keep every order moving.",
    create: "Create order",
    searchLabel: "Search",
    searchPlaceholder: "Order number or customer",
    statusLabel: "Status",
    paymentLabel: "Payment",
    fromLabel: "From",
    reset: "Reset filters",
  },
  placeholder: {
    eyebrow: "Foundation preview",
    titleSuffix: "is ready for its build phase",
    subtitle:
      "The navigation, layout, tokens, and responsive shell are in place. Live workflows arrive in the scheduled phase.",
  },
} as const;
