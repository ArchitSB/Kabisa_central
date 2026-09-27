import { lazy, Suspense } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  HeartPulse,
  Pill,
  ShieldCheck,
  Stethoscope,
  Syringe,
  Tablets,
  Truck,
  Zap,
  PackageCheck,
  Plus,
  Leaf,
} from "lucide-react";
import { getHome, heroImageUrl } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { t } from "../i18n";
import { ProductCard } from "../components/product-card";
import { ErrorState, SectionHeading, Skeleton } from "../components/ui";
const MarketingMotion = lazy(() => import("../components/marketing-motion"));
const categoryIcons = [HeartPulse, Tablets, Pill, Leaf, Syringe, Stethoscope];
export default function Home() {
  const { authenticated } = useStore();
  const query = useQuery({
    queryKey: ["home", authenticated],
    queryFn: getHome,
  });
  useSeo();
  if (query.isLoading)
    return (
      <div className="container section">
        <div className="skeleton hero-skeleton" />
        <Skeleton />
      </div>
    );
  if (query.isError)
    return (
      <div className="container">
        <ErrorState error={query.error} retry={() => query.refetch()} />
      </div>
    );
  const home = query.data!;
  const cfg = home.config.settings;
  const hero = home.banners.find((b) => b.placement === "HOME_HERO");
  const strip = home.banners.find((b) => b.placement === "HOME_STRIP");
  const badges = Array.isArray(cfg.trust_badges)
    ? (cfg.trust_badges as { title: string; description: string }[])
    : [];
  const trustIcons = [ShieldCheck, PackageCheck, Truck, Stethoscope];
  return (
    <>
      <Suspense fallback={null}>
        <MarketingMotion />
      </Suspense>
      <div className="container home-content">
        {hero ? (
          <section className="hero">
            <div className="hero-copy">
              <p className="eyebrow">
                <span className="little-line" />
                {String(cfg.home_eyebrow)}
              </p>
              <h1>
                {hero.title?.split("\n").map((line, i) => (
                  <span key={i} className={i ? "serif-soft" : ""}>
                    {line}
                    {i === 0 && <br />}
                  </span>
                ))}
              </h1>
              <p className="hero-description">{hero.subtitle}</p>
              <div className="hero-actions">
                <Link
                  className="btn hero-button"
                  to={hero.link_url || "/catalog"}
                >
                  {String(hero.link_label || t("action.browse"))}
                  <ArrowRight size={18} />
                </Link>
                <Link className="hero-secondary" to="/quick-order">
                  <Zap size={17} />
                  {t("nav.quick")}
                </Link>
              </div>
              <div className="hero-footnote">
                <span className="tiny-crosses">
                  <Plus />
                  <Plus />
                  <Plus />
                </span>
                {Number(cfg.facility_count) > 0 ? (
                  <p>
                    <strong>{Number(cfg.facility_count)}+</strong>{" "}
                    {t("home.facilities")}
                  </p>
                ) : (
                  <p>{String(cfg.home_trust_body)}</p>
                )}
              </div>
            </div>
            <div className="hero-art">
              <picture>
                <source
                  media="(max-width: 767px)"
                  srcSet={heroImageUrl(true)}
                />
                <img
                  className="hero-photo"
                  src={heroImageUrl()}
                  alt={t("home.illustration")}
                  {...{ fetchpriority: "high" }}
                  width="900"
                  height="900"
                />
              </picture>
              <span className="hero-art-index">01 / KABISA</span>
              <div className="care-seal">
                <ShieldCheck size={26} strokeWidth={1.4} />
                <span>{String(cfg.home_trust_title)}</span>
              </div>
              <div className="hero-corner-mark">
                <Plus strokeWidth={1} />
              </div>
            </div>
          </section>
        ) : (
          <section className="empty-state">
            <h1>{t("home.noContent")}</h1>
            <Link className="btn" to="/catalog">
              {t("action.browse")}
            </Link>
          </section>
        )}
        {badges.length > 0 && (
          <section className="trust-strip">
            {badges.slice(0, 4).map((badge, i) => {
              const Icon = trustIcons[i];
              return (
                <div key={i}>
                  <span>
                    <Icon size={23} strokeWidth={1.5} />
                  </span>
                  <div>
                    <h3>{badge.title}</h3>
                    <p>{badge.description}</p>
                  </div>
                </div>
              );
            })}
          </section>
        )}
        <section className="section category-section" data-reveal>
          <SectionHeading
            eyebrow={t("home.browseCare")}
            title={String(cfg.home_categories_title)}
            body={String(cfg.home_categories_subtitle)}
            to="/catalog"
          />
          <div className="category-grid">
            {home.categories.slice(0, 6).map((category, i) => {
              const Icon = categoryIcons[i % categoryIcons.length];
              return (
                <Link
                  key={category.id}
                  to={`/catalog?category=${category.slug}`}
                  className={`category-card category-${i}`}
                >
                  <span className="category-icon">
                    <Icon size={30} strokeWidth={1.3} />
                  </span>
                  <span>{category.name}</span>
                  <ArrowUpRight size={17} />
                </Link>
              );
            })}
          </div>
        </section>
        <section className="section products-section" data-reveal>
          <SectionHeading
            eyebrow={t("home.featured")}
            title={
              home.collections[0]?.title || String(cfg.home_featured_title)
            }
            body={
              home.collections[0]?.subtitle ||
              String(cfg.home_featured_subtitle)
            }
            to="/catalog"
          />
          <div className="product-grid">
            {(home.collections[0]?.products?.length
              ? home.collections[0].products
              : home.featured
            )
              .slice(0, 4)
              .map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
          </div>
        </section>
        <section className="quick-order-banner" data-reveal>
          <div className="quick-illustration">
            <div className="list-paper">
              <span />
              <div>
                <span />
                <i />
              </div>
              <div>
                <span />
                <i />
              </div>
              <div>
                <span />
                <i />
              </div>
              <span className="paper-check">
                <PackageCheck size={27} />
              </span>
            </div>
            <span className="quick-orbit" />
          </div>
          <div>
            <p className="eyebrow">
              <Zap size={13} />
              {t("nav.quick")}
            </p>
            <h2>{strip?.title || String(cfg.home_quick_title)}</h2>
            <p>{strip?.subtitle || String(cfg.home_quick_body)}</p>
          </div>
          <Link className="btn" to={strip?.link_url || "/quick-order"}>
            {String(strip?.link_label || t("home.quickLink"))}
            <ArrowRight size={18} />
          </Link>
        </section>
        {home.collections.slice(1).map((collection) =>
          collection.products?.length ? (
            <section
              className="section products-section"
              data-reveal
              key={collection.id}
            >
              <SectionHeading
                title={collection.title || ""}
                body={collection.subtitle}
                to="/catalog?sort=newest"
              />
              <div className="product-grid">
                {collection.products.slice(0, 4).map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
            </section>
          ) : null,
        )}
        {home.brands.length > 0 && (
          <section className="brand-section" data-reveal>
            <p className="eyebrow">{t("home.brandLabel")}</p>
            <div className="brand-rail">
              {home.brands.slice(0, 6).map((brand) => (
                <Link to={`/catalog?brand=${brand.slug}`} key={brand.id}>
                  {brand.name}
                </Link>
              ))}
            </div>
          </section>
        )}
        {home.testimonials.length > 0 && (
          <section className="section testimonials">
            <SectionHeading title={t("home.customerStories")} />
            {home.testimonials.map((item) => (
              <blockquote key={item.id}>
                <p>“{item.quote}”</p>
                <footer>
                  {item.author} · {item.organisation}
                </footer>
              </blockquote>
            ))}
          </section>
        )}
        <section className="care-banner" data-reveal>
          <span className="care-banner-icon">
            <HeartPulse size={54} strokeWidth={1} />
          </span>
          <div>
            <p className="eyebrow">{t("home.trust")}</p>
            <h2>{String(cfg.home_trust_title)}</h2>
            <p>{String(cfg.home_trust_body)}</p>
          </div>
          <Link
            className="text-link"
            to={authenticated ? "/catalog" : "/register"}
          >
            {authenticated ? t("action.browse") : t("home.accountLink")}
            <ArrowUpRight size={20} />
          </Link>
        </section>
      </div>
    </>
  );
}
