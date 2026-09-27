import { useSyncExternalStore } from "react";
import { getLocale, subscribeLocale } from "./i18n";
import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import "./fonts.css";
import "./styles.css";
import { queryClient } from "./lib/api";
import { StoreProvider, useStore } from "./lib/store";
import { Layout } from "./components/layout";
import { ErrorBoundary, Skeleton } from "./components/ui";
// Home is the critical entry screen; keeping its small component eager avoids a request waterfall.
import Home from "./pages/home";
const Catalog = lazy(() => import("./pages/catalog"));
const Product = lazy(() => import("./pages/product"));
const QuickOrder = lazy(() => import("./pages/quick-order"));
const Basket = lazy(() => import("./pages/cart"));
const Checkout = lazy(() => import("./pages/checkout"));
const Account = lazy(() => import("./pages/account"));
const Order = lazy(() => import("./pages/orders"));
const Auth = lazy(() => import("./pages/auth"));
const Content = lazy(() => import("./pages/content"));
const NotFound = lazy(() =>
  import("./pages/content").then((m) => ({ default: m.NotFound })),
);
function Protected() {
  const { authenticated } = useStore();
  const location = useLocation();
  return authenticated ? (
    <Outlet />
  ) : (
    <Navigate
      replace
      to={`/login?returnTo=${encodeURIComponent(location.pathname)}`}
    />
  );
}
function AuthRoute() {
  const location = useLocation();
  return <Auth key={location.pathname} />;
}
function App() {
  const locale = useSyncExternalStore(subscribeLocale, getLocale);
  return (
    <QueryClientProvider client={queryClient}>
      <StoreProvider>
        <BrowserRouter
          key={locale}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <ErrorBoundary>
            <Suspense
              fallback={
                <div className="container section">
                  <Skeleton />
                </div>
              }
            >
              <Routes>
                <Route element={<Layout />}>
                  <Route index element={<Home />} />
                  <Route path="catalog" element={<Catalog />} />
                  <Route path="product/:slug" element={<Product />} />
                  <Route path="quick-order" element={<QuickOrder />} />
                  <Route path="cart" element={<Basket />} />
                  {["login", "register", "forgot-password"].map((path) => (
                    <Route key={path} path={path} element={<AuthRoute />} />
                  ))}
                  <Route path="pages/:slug" element={<Content />} />
                  <Route path="faq" element={<Content />} />
                  <Route path="contact" element={<Content />} />
                  <Route element={<Protected />}>
                    <Route path="checkout" element={<Checkout />} />
                    <Route path="account" element={<Account />} />
                    <Route path="account/orders/:id" element={<Order />} />
                    <Route path="account/:section" element={<Account />} />
                    <Route path="order-confirmed/:id" element={<Order />} />
                  </Route>
                  <Route path="*" element={<NotFound />} />
                </Route>
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </BrowserRouter>
        <Toaster position="bottom-right" richColors closeButton />
      </StoreProvider>
    </QueryClientProvider>
  );
}
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
if ("serviceWorker" in navigator && import.meta.env.PROD)
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
