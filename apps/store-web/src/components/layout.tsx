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
  ChevronDown,
  Menu,
  Search,
  ShoppingBag,
  UserRound,
  X,
  Zap,
  Phone,
  Mail,
  ArrowUp,
  Grid2X2,
} from "lucide-react";
import { cartSummary } from "@kabisa/core";
import { getHome } from "../lib/api";
import { useStore } from "../lib/store";
import { getLocale, setLocale, t } from "../i18n";
import { Empty, OfflineNotice } from "./ui";

export function Brand() {
  return (
    <Link to="/" className="brand">
      <span className="brand-icon" aria-hidden="true">
        K<span />
      </span>
      <span>
        kabisa<span className="brand-dot">.</span>
        <small>PHARMACY</small>
      </span>
    </Link>
  );
}
export function Layout() {
  const { cart, authenticated, config } = useStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [search, setSearch] = useState("");
  const [mobile, setMobile] = useState(false);
  const [language, setLanguage] = useState(getLocale);
  const home = useQuery({
    queryKey: ["home", authenticated],
    queryFn: getHome,
    enabled: !config?.settings.maintenance_mode,
  });
  const menus = home.data?.menus.filter((m) => m.placement === "HEADER") ?? [];
  const footerMenus =
    home.data?.menus.filter((m) => m.placement === "FOOTER") ?? [];
  const cfg = config?.settings;
  const company = config?.company;
  useEffect(() => {
    setMobile(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location.pathname]);
  useEffect(() => {
    const focusSearch = (event: KeyboardEvent) => {
      const tag = (event.target as HTMLElement).tagName;
      if (
        event.key === "/" &&
        !["INPUT", "TEXTAREA", "SELECT"].includes(tag) &&
        !(event.target as HTMLElement).isContentEditable
      ) {
        event.preventDefault();
        document
          .querySelector<HTMLInputElement>(".header-search input")
          ?.focus();
      }
    };
    window.addEventListener("keydown", focusSearch);
    return () => window.removeEventListener("keydown", focusSearch);
  }, []);
  function submit(e: FormEvent) {
    e.preventDefault();
    navigate(`/catalog?search=${encodeURIComponent(search)}`);
  }
  if (cfg?.maintenance_mode)
    return (
      <main className="maintenance container">
        <Brand />
        <Empty
          title={t("error.maintenance")}
          body={String(cfg.maintenance_message)}
          action={
            cfg.support_email ? (
              <a className="btn" href={`mailto:${cfg.support_email}`}>
                {t("page.email")}
              </a>
            ) : undefined
          }
        />
      </main>
    );
  return (
    <>
      <a className="skip-link" href="#main-content">
        {t("nav.skip")}
      </a>
      <OfflineNotice />
      {home.data?.announcements[0] && (
        <div className="announcement">
          <span>{home.data.announcements[0].message}</span>
          <ArrowRight size={14} />
        </div>
      )}
      <header className="site-header">
        <div className="container header-main">
          <Brand />
          <form className="header-search" role="search" onSubmit={submit}>
            <Search size={19} />
            <input
              aria-label={t("nav.search")}
              placeholder={t("nav.search")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <kbd>/</kbd>
            <button type="submit" className="sr-only">
              {t("nav.search")}
            </button>
          </form>
          <div className="header-actions">
            <select
              aria-label={t("nav.language")}
              value={language}
              onChange={(e) => {
                setLocale(e.target.value);
                setLanguage(e.target.value);
              }}
            >
              <option value="en">EN</option>
              <option value="sw">SW</option>
            </select>
            <Link
              className="account-link"
              to={authenticated ? "/account" : "/login"}
            >
              <UserRound size={21} />
              <span>{authenticated ? t("nav.account") : t("nav.login")}</span>
            </Link>
            <Link
              className="cart-link"
              to="/cart"
              aria-label={`${t("nav.cart")}, ${cartSummary(cart.items).quantity}`}
            >
              <ShoppingBag size={21} />
              <span className="cart-count">
                {cartSummary(cart.items).quantity}
              </span>
            </Link>
            <Dialog.Root open={mobile} onOpenChange={setMobile}>
              <Dialog.Trigger asChild>
                <button
                  className="mobile-menu icon-button"
                  aria-label={t("nav.menu")}
                >
                  <Menu />
                </button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="drawer-overlay" />
                <Dialog.Content className="mobile-drawer">
                  <Dialog.Title className="sr-only">
                    {t("nav.menu")}
                  </Dialog.Title>
                  <Dialog.Description className="sr-only">
                    {t("nav.catalog")}
                  </Dialog.Description>
                  <div className="drawer-top">
                    <Brand />
                    <Dialog.Close
                      className="icon-button"
                      aria-label={t("action.close")}
                    >
                      <X />
                    </Dialog.Close>
                  </div>
                  <nav>
                    {menus.map((m) => (
                      <Link key={m.id} to={m.link_url || "/"}>
                        {m.label}
                        <ArrowUpRight size={18} />
                      </Link>
                    ))}
                    <Link to="/account">
                      {t("nav.account")}
                      <UserRound size={18} />
                    </Link>
                  </nav>
                  <Link className="btn" to="/quick-order">
                    <Zap size={16} />
                    {t("nav.quick")}
                  </Link>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
          </div>
        </div>
        <div className="header-navigation">
          <div className="container navigation-inner">
            <nav>
              {menus.map((m, i) => (
                <NavLink
                  key={m.id}
                  className={i === 0 ? "all-products" : ""}
                  to={m.link_url || "/"}
                >
                  {i === 0 && <Grid2X2 size={17} />}
                  <span>{m.label}</span>
                  {i === 0 && <ChevronDown size={14} />}
                </NavLink>
              ))}
            </nav>
            {cfg?.support_phone && (
              <a className="header-help" href={`tel:${cfg.support_phone}`}>
                <Phone size={14} />
                <span>
                  {t("nav.support")}{" "}
                  <strong>{String(cfg.support_phone)}</strong>
                </span>
              </a>
            )}
            <Link to="/quick-order" className="quick-nav">
              <Zap size={15} />
              {t("nav.quick")}
            </Link>
          </div>
        </div>
        <form
          className="mobile-search container"
          role="search"
          onSubmit={submit}
        >
          <Search size={18} />
          <input
            aria-label={t("nav.search")}
            placeholder={t("nav.search")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit" aria-label={t("nav.search")}>
            <ArrowRight size={18} />
          </button>
        </form>
      </header>
      <main id="main-content" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="container">
          <div className="footer-main">
            <div className="footer-brand">
              <Brand />
              <p>{String(cfg?.footer_description ?? "")}</p>
              {cfg?.support_phone && (
                <a href={`tel:${cfg.support_phone}`}>
                  <Phone size={15} />
                  {String(cfg.support_phone)}
                </a>
              )}
              {cfg?.support_email && (
                <a href={`mailto:${cfg.support_email}`}>
                  <Mail size={15} />
                  {String(cfg.support_email)}
                </a>
              )}
            </div>
            <div>
              <h3>{t("footer.explore")}</h3>
              {footerMenus.map((m) => (
                <Link key={m.id} to={m.link_url || "/"}>
                  {m.label}
                </Link>
              ))}
            </div>
            <div>
              <h3>{t("footer.account")}</h3>
              <Link to="/account/orders">{t("account.orders")}</Link>
              <Link to="/quick-order">{t("nav.quick")}</Link>
              <Link to="/account/verification">
                {t("account.verification")}
              </Link>
              <Link to="/register">{t("nav.register")}</Link>
            </div>
            <div>
              <h3>{t("footer.legal")}</h3>
              <p>{company?.company_name}</p>
              <p>{company?.company_address}</p>
              {company?.company_tin && <p>TIN: {company.company_tin}</p>}
              {company?.company_licence && <p>{company.company_licence}</p>}
              {cfg?.business_hours && <p>{String(cfg.business_hours)}</p>}
            </div>
          </div>
          <div className="footer-bottom">
            <span>
              © {new Date().getFullYear()} {company?.company_name || "Kabisa"}.{" "}
              {t("footer.rights")}
            </span>
            <span>{t("footer.powered")}</span>
            <button
              onClick={() =>
                window.scrollTo({
                  top: 0,
                  behavior: matchMedia("(prefers-reduced-motion: reduce)")
                    .matches
                    ? "instant"
                    : "smooth",
                })
              }
            >
              {t("footer.backTop")}
              <ArrowUp size={14} />
            </button>
          </div>
        </div>
      </footer>
      <nav className="mobile-bottom-nav">
        <NavLink to="/" end>
          <Grid2X2 size={20} />
          {t("nav.home")}
        </NavLink>
        <NavLink to="/catalog">
          <Search size={20} />
          {t("nav.catalog")}
        </NavLink>
        <NavLink to="/quick-order">
          <Zap size={20} />
          {t("nav.quick")}
        </NavLink>
        <NavLink to="/cart">
          <ShoppingBag size={20} />
          {t("nav.cart")}
        </NavLink>
        <NavLink to="/account">
          <UserRound size={20} />
          {t("nav.account")}
        </NavLink>
      </nav>
    </>
  );
}
