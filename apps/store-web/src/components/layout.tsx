import { StaleDataBanner } from "./stale-data-banner";
import { useEffect, useState, type FormEvent } from "react";
import {
  Link,
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ArrowRight,
  ArrowUpRight,
  Menu,
  Search,
  ShoppingBag,
  UserRound,
  X,
  Zap,
  Phone,
  Mail,
  Grid2X2,
  Bell,
  ShieldCheck,
  MapPin,
} from "lucide-react";
import { PageMotion, CartCount } from "./store-motion";
import { cartSummary } from "@kabisa/core";
import { getHome } from "../lib/api";
import { useStore } from "../lib/store";
import { Empty, OfflineNotice } from "./ui";

export function Brand() {
  return (
    <Link to="/" className="brand" aria-label="Kabisa — home">
      <img
        src="/images/kabisa-logo.png"
        width="176"
        height="80"
        alt="Kabisa — One step for millions"
      />
    </Link>
  );
}
export function Layout() {
  const { cart, authenticated, customer, config } = useStore();
  const approved = customer?.customer.status === "VERIFIED";
  const navigate = useNavigate();
  const location = useLocation();
  const [search, setSearch] = useState("");
  const [mobile, setMobile] = useState(false);
  const home = useQuery({
    queryKey: ["home", authenticated, customer?.customer.status],
    queryFn: getHome,
    enabled: !config?.settings.maintenance_mode,
  });
  const cfg = config?.settings;
  const supportEmail = String(
    cfg?.support_email || config?.company.company_email || "",
  );
  const supportPhone = String(
    cfg?.support_phone || config?.company.company_phone || "",
  );
  const defaultNav = approved
    ? [
        ["/", "Overview"],
        ["/catalog", "All products"],
        ["/quick-order", "Quick order"],
        ["/account/orders", "My orders"],
        ["/account/favourites", "Saved products"],
      ]
    : [
        ["/", "Home"],
        ["/pages/about", "About Kabisa"],
        ["/faq", "How it works"],
        ["/contact", "Contact us"],
      ];
  const managedNav =
    home.data?.menus
      .filter(
        (m) =>
          m.placement === "HEADER" &&
          m.label &&
          m.link_url &&
          (approved ||
            !["/catalog", "/quick-order", "/cart"].some((prefix) =>
              m.link_url!.startsWith(prefix),
            )),
      )
      .map((m) => [m.link_url!, m.label!]) || [];
  const nav = managedNav.length
    ? [
        ["/", approved ? "Overview" : "Home"],
        ...managedNav.filter(([url]) => url !== "/"),
        ...(approved ? [["/account/orders", "My orders"]] : []),
      ]
    : defaultNav;
  const footerNav = home.data?.menus.filter(
    (m) => m.placement === "FOOTER" && m.label && m.link_url,
  );
  useEffect(() => {
    setMobile(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location.pathname]);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (
        event.key === "/" &&
        !["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) &&
        !target.isContentEditable
      ) {
        event.preventDefault();
        document
          .querySelector<HTMLInputElement>(".header-search input")
          ?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
  function submit(event: FormEvent) {
    event.preventDefault();
    navigate(`/catalog?search=${encodeURIComponent(search)}`);
  }
  if (cfg?.maintenance_mode)
    return (
      <main className="maintenance container">
        <Brand />
        <Empty
          title="We’ll be back shortly"
          body={String(cfg.maintenance_message)}
        />
      </main>
    );
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <OfflineNotice />
      <div className="utility-bar">
        <div className="container">
          <span>
            <MapPin size={13} /> Supporting healthcare businesses across
            Tanzania
          </span>
          <Link to="/contact">
            Talk to our team <ArrowUpRight size={13} />
          </Link>
        </div>
      </div>
      <header className="site-header">
        <div className="container header-main">
          <Brand />
          {approved ? (
            <form className="header-search" role="search" onSubmit={submit}>
              <Search size={20} />
              <input
                aria-label="Search products"
                placeholder="Search medicines, brands or product codes…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <button type="submit" aria-label="Search">
                <ArrowRight size={18} />
              </button>
            </form>
          ) : (
            <p className="header-purpose">
              Your partner in
              <br />
              <strong>better healthcare.</strong>
            </p>
          )}
          <div className="header-actions">
            {authenticated && (
              <Link
                className="icon-button"
                to="/account/notifications"
                aria-label="Notifications"
              >
                <Bell size={21} />
              </Link>
            )}
            <Link
              className="account-link"
              to={
                authenticated
                  ? approved
                    ? "/account"
                    : "/account/verification"
                  : "/login"
              }
            >
              <UserRound size={21} />
              <span>
                {authenticated
                  ? approved
                    ? "My account"
                    : "My application"
                  : "Sign in"}
              </span>
            </Link>
            {approved ? (
              <Link
                className="cart-link"
                to="/cart"
                aria-label={`Basket, ${cartSummary(cart.items).quantity} items`}
              >
                <ShoppingBag size={21} />
                <CartCount value={cartSummary(cart.items).quantity} />
              </Link>
            ) : (
              !authenticated && (
                <Link className="btn header-apply" to="/register">
                  Open an account <ArrowUpRight size={16} />
                </Link>
              )
            )}
            <Dialog.Root open={mobile} onOpenChange={setMobile}>
              <Dialog.Trigger asChild>
                <button
                  className="mobile-menu icon-button"
                  aria-label="Open menu"
                >
                  <Menu />
                </button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="drawer-overlay" />
                <Dialog.Content className="mobile-drawer">
                  <Dialog.Title className="sr-only">Navigation</Dialog.Title>
                  <Dialog.Description className="sr-only">
                    Explore Kabisa and manage your business account.
                  </Dialog.Description>
                  <div className="drawer-top">
                    <Brand />
                    <Dialog.Close
                      className="icon-button"
                      aria-label="Close menu"
                    >
                      <X />
                    </Dialog.Close>
                  </div>
                  <nav>
                    {nav.map(([url, label]) => (
                      <Link to={url} key={url}>
                        {label}
                        <ArrowUpRight size={18} />
                      </Link>
                    ))}
                    <Link
                      to={authenticated ? "/account/verification" : "/register"}
                    >
                      {authenticated ? "My application" : "Open an account"}
                      <ShieldCheck size={18} />
                    </Link>
                  </nav>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
          </div>
        </div>
        <div className="header-navigation">
          <div className="container navigation-inner">
            <nav>
              {nav.map(([url, label], i) => (
                <NavLink end={url === "/"} key={url} to={url}>
                  {approved && i === 1 && <Grid2X2 size={16} />}
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>
            <Link
              className="header-help"
              to={approved ? "/quick-order" : "/register"}
            >
              {approved ? <Zap size={15} /> : <ShieldCheck size={15} />}
              <span>
                {approved
                  ? "Have a list? Order in bulk"
                  : "Exclusively for healthcare businesses"}
              </span>
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </header>
      {home.data?.announcements[0] && approved && (
        <div className="store-announcement">
          <div className="container">
            <span>{home.data.announcements[0].message}</span>
            <Link to="/catalog">
              Explore <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      )}
      <main id="main-content" tabIndex={-1}>
        <PageMotion key={location.pathname}>
          <StaleDataBanner />
          <Outlet />
        </PageMotion>
      </main>
      <footer className="site-footer">
        <div className="container">
          <div className="footer-main">
            <div className="footer-brand">
              <Brand />
              <p>
                {String(
                  cfg?.footer_description ||
                    "One step for millions. Connecting the people who care with the supplies they need.",
                )}
              </p>
              <span className="footer-location">
                <MapPin size={15} /> Dar es Salaam, Tanzania
              </span>
            </div>
            <div>
              <h3>Explore Kabisa</h3>
              {footerNav?.length ? (
                footerNav.map((m) => (
                  <Link key={m.id} to={m.link_url!}>
                    {m.label}
                  </Link>
                ))
              ) : (
                <>
                  <Link to="/pages/about">Our company</Link>
                  <Link to="/catalog">Product catalog</Link>
                  <Link to="/pages/delivery">Delivery information</Link>
                  <Link to="/faq">Frequently asked questions</Link>
                </>
              )}
            </div>
            <div>
              <h3>Your business</h3>
              <Link to="/register">Become a customer</Link>
              <Link to="/account/verification">Business verification</Link>
              <Link to="/account/orders">Track an order</Link>
              <Link to="/account/security">Account security</Link>
            </div>
            <div>
              <h3>Let’s talk</h3>
              <p>
                Product enquiries, account questions
                <br />
                or help with your next order.
              </p>
              {supportPhone && (
                <a href={`tel:${supportPhone}`}>
                  <Phone size={15} />
                  {supportPhone}
                </a>
              )}
              {supportEmail && (
                <a href={`mailto:${supportEmail}`}>
                  <Mail size={15} />
                  {supportEmail}
                </a>
              )}
              <Link className="text-link" to="/contact">
                Contact the team <ArrowUpRight size={16} />
              </Link>
            </div>
          </div>
          <div className="footer-bottom">
            <span>
              © {new Date().getFullYear()}{" "}
              {config?.company.company_name || "Kabisa Pharmaceuticals"}. All
              rights reserved.
            </span>
            <span>Built around better care.</span>
          </div>
        </div>
      </footer>
    </>
  );
}
