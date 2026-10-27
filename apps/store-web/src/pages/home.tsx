import { Link, Navigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  ShieldCheck,
  PackageCheck,
  Headphones,
  Zap,
  FileCheck2,
  UserRoundCheck,
  Pill,
  Stethoscope,
  Leaf,
  Syringe,
  Plus,
  ClipboardList,
  Bookmark,
  Package,
} from "lucide-react";
import type { Page, StoreOrder } from "@kabisa/api-client";
import { api, assetUrl, getHome } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { ErrorState, Skeleton, Badge } from "../components/ui";
import { Reveal } from "../components/store-motion";
import { ProductCard } from "../components/product-card";
const featuredDepartments = [
  "Hospital Consumables",
  "Medical Equipment",
  "Diagnostics",
  "Wound Care",
  "Personal Care & Hygiene",
  "Vitamins Minerals & Nutritional Supplements",
];
function departmentRank(name: string) {
  const rank = featuredDepartments.indexOf(name);
  return rank < 0 ? featuredDepartments.length : rank;
}
const categoryIcons = [Syringe, Stethoscope, Plus, Package, Leaf, Pill];
const steps = [
  {
    icon: UserRoundCheck,
    title: "Tell us about your business",
    body: "Verify your phone or email and create your business account.",
  },
  {
    icon: FileCheck2,
    title: "Submit your certificates",
    body: "Upload your TIN, TMDA, Pharmacy Council and TBS documents securely.",
  },
  {
    icon: ShieldCheck,
    title: "Get approved. Get supplied.",
    body: "Our team reviews your application. Once approved, your store is ready.",
  },
];
export default function Home() {
  const { authenticated, customer } = useStore();
  const approved = customer?.customer.status === "VERIFIED";
  const query = useQuery({
    queryKey: ["home", authenticated, customer?.customer.status],
    queryFn: getHome,
  });
  const orders = useQuery({
    queryKey: ["orders", "home"],
    queryFn: () => api.get<Page<StoreOrder>>("/orders?page_size=3"),
    enabled: approved,
  });
  useSeo("One step for millions");
  if (authenticated && customer && !approved)
    return <Navigate to="/account/verification" replace />;
  if (query.isError && query.data === undefined)
    return (
      <div className="container section">
        <ErrorState error={query.error} retry={() => query.refetch()} />
      </div>
    );
  const home = query.data;
  const hero = home?.banners.find((b) => b.placement === "HOME_HERO");
  const products = home?.collections[0]?.products?.length
    ? home.collections[0].products
    : home?.featured || [];
  const heroImage =
    assetUrl(hero?.image_path) || "/images/pharmacy-partner.webp";
  return (
    <div className="store-home">
      <div className="container">
        {approved && (
          <div className="welcome-line">
            <div>
              <p className="eyebrow">YOUR KABISA WORKSPACE</p>
              <h1>Karibu, {customer?.full_name.split(" ")[0]}.</h1>
              <p>
                {customer?.customer.business_name} <span> / </span>{" "}
                {customer?.customer.price_tier} pricing
              </p>
            </div>
            <Link className="btn secondary" to="/account/orders">
              <Package size={16} /> My orders <ArrowUpRight size={16} />
            </Link>
          </div>
        )}
        <section className={`partner-hero ${approved ? "compact" : ""}`}>
          <div className="partner-hero-copy">
            <p className="eyebrow">
              <span className="red-rule" />
              {approved
                ? "LESS ADMIN. MORE CARE."
                : "FOR THE PEOPLE BEHIND BETTER CARE"}
            </p>
            {approved ? (
              <h2>
                Your next order.
                <br />
                <em>A simpler day.</em>
              </h2>
            ) : (
              <h1>
                {hero?.title ? (
                  hero.title.split("\n").map((line, i) => (
                    <span key={i}>
                      {line}
                      {i === 0 && <br />}
                    </span>
                  ))
                ) : (
                  <>
                    Better supplied.
                    <br />
                    <em>Better together.</em>
                  </>
                )}
              </h1>
            )}
            <p className="hero-description">
              {approved
                ? "Your facility pricing, everyday essentials and order updates. All together, in one place."
                : hero?.subtitle ||
                  "From your first patient to your last order of the day. We help Tanzania’s healthcare businesses keep care moving."}
            </p>
            <div className="hero-actions">
              <Link className="btn" to={approved ? "/catalog" : "/register"}>
                {approved ? "Shop your catalog" : "Open a business account"}
                <ArrowUpRight size={18} />
              </Link>
              <Link
                className="text-link"
                to={approved ? "/quick-order" : "/login"}
              >
                {approved ? <Zap size={16} /> : null}
                {approved ? "Quick order" : "Already a customer? Sign in"}
              </Link>
            </div>
            <div className="hero-assurance">
              <ShieldCheck size={18} />
              <span>
                {approved
                  ? "Your business is verified. You’re ready to order."
                  : "A dedicated supply partner. A verified business community."}
              </span>
            </div>
          </div>
          <div className="partner-hero-image">
            <img
              src={heroImage}
              alt="Illustrative portrait of a pharmacist preparing supplies in a Tanzanian pharmacy"
              width="1200"
              height="800"
              {...{ fetchpriority: "high" }}
            />
            <div className="photo-caption">
              <span className="photo-mark">+</span>
              <div>
                <strong>
                  Behind every order,
                  <br />
                  there’s someone who cares.
                </strong>
                <span>ONE STEP FOR MILLIONS</span>
              </div>
            </div>
            <span className="photo-credit">Illustrative image</span>
          </div>
        </section>
        <div className="service-strip">
          {[
            {
              icon: ShieldCheck,
              title: "Verified business access",
              body: "A trusted space for healthcare procurement",
            },
            {
              icon: PackageCheck,
              title: "Your supplies, connected",
              body: "Availability and pricing in one place",
            },
            {
              icon: Headphones,
              title: "People you can talk to",
              body: "Support from the Kabisa team",
            },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title}>
              <Icon size={25} strokeWidth={1.5} />
              <span>
                <strong>{title}</strong>
                <small>{body}</small>
              </span>
            </div>
          ))}
        </div>
        {approved && (
          <div className="workspace-shortcuts">
            {[
              {
                url: "/quick-order",
                icon: Zap,
                title: "Order from a list",
                body: "Paste product codes and quantities",
              },
              {
                url: "/account/templates",
                icon: Bookmark,
                title: "Your saved baskets",
                body: "Make repeat purchases effortless",
              },
              {
                url: "/account/orders",
                icon: ClipboardList,
                title: "Follow your orders",
                body: orders.data
                  ? `${orders.data.total} orders in your account`
                  : "From approval to delivery",
              },
            ].map(({ url, icon: Icon, title, body }) => (
              <Link key={url} to={url}>
                <Icon size={22} />
                <div>
                  <strong>{title}</strong>
                  <p>{body}</p>
                </div>
                <ArrowUpRight size={18} />
              </Link>
            ))}
          </div>
        )}
        <Reveal as="section" className="store-section">
          <div className="store-section-head">
            <div>
              <p className="eyebrow">A WELL-STOCKED WORLD OF CARE</p>
              <h2>
                {approved
                  ? "What does your business need?"
                  : "Everyday essentials. Specialist care."}
              </h2>
            </div>
            {approved && (
              <Link className="text-link" to="/catalog">
                All categories <ArrowRight size={16} />
              </Link>
            )}
          </div>
          {query.isLoading ? (
            <Skeleton cards={6} />
          ) : (
            <div className="department-grid">
              {home?.categories
                .slice()
                .sort((a, b) => departmentRank(a.name) - departmentRank(b.name))
                .slice(0, 6)
                .map((c, i) => {
                  const Icon = categoryIcons[i % categoryIcons.length];
                  return (
                    <Link
                      key={c.id}
                      to={
                        approved ? `/catalog?category=${c.slug}` : "/register"
                      }
                      className="department-card"
                    >
                      <span className={`department-icon tone-${i}`}>
                        <Icon size={32} strokeWidth={1.3} />
                      </span>
                      <strong>{c.name}</strong>
                      <span className="department-link">
                        {approved ? "Explore products" : "Join to explore"}
                        <ArrowUpRight size={15} />
                      </span>
                    </Link>
                  );
                })}
            </div>
          )}
        </Reveal>
        {approved ? (
          <>
            <Reveal as="section" className="store-section">
              <div className="store-section-head">
                <div>
                  <p className="eyebrow">READY FOR YOUR NEXT ORDER</p>
                  <h2>
                    {home?.collections[0]?.title || "Selected for your shelves"}
                  </h2>
                  <p>
                    {home?.collections[0]?.subtitle ||
                      "Explore products with your business pricing."}
                  </p>
                </div>
                <Link className="text-link" to="/catalog">
                  View all products <ArrowRight size={16} />
                </Link>
              </div>
              <div className="product-grid">
                {products.slice(0, 8).map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            </Reveal>
            <Reveal as="section" className="restock-banner">
              <div className="restock-icon">
                <ClipboardList size={50} strokeWidth={1} />
              </div>
              <div>
                <p className="eyebrow">YOUR TIME BELONGS WITH YOUR PATIENTS</p>
                <h2>Long list? Short work.</h2>
                <p>
                  Paste your product codes and quantities. Review your matches.
                  Add them together.
                </p>
              </div>
              <Link className="btn" to="/quick-order">
                Start a quick order <Zap size={17} />
              </Link>
            </Reveal>
            {home?.collections
              .slice(1)
              .filter((c) => c.products?.length)
              .map((c) => (
                <Reveal as="section" className="store-section" key={c.id}>
                  <div className="store-section-head">
                    <div>
                      <p className="eyebrow">DISCOVER MORE</p>
                      <h2>{c.title}</h2>
                      <p>{c.subtitle}</p>
                    </div>
                    <Link className="text-link" to="/catalog?sort=newest">
                      Explore <ArrowRight size={16} />
                    </Link>
                  </div>
                  <div className="product-grid">
                    {c.products?.slice(0, 4).map((p) => (
                      <ProductCard key={p.id} product={p} />
                    ))}
                  </div>
                </Reveal>
              ))}
          </>
        ) : (
          <>
            <Reveal as="section" className="join-section" id="how-it-works">
              <div className="store-section-head">
                <div>
                  <p className="eyebrow">
                    A SIMPLE START TO A LASTING PARTNERSHIP
                  </p>
                  <h2>Your business belongs here.</h2>
                </div>
                <p>
                  For DLDM outlets, community pharmacies
                  <br />
                  and wholesale healthcare businesses.
                </p>
              </div>
              <div className="join-steps">
                {steps.map(({ icon: Icon, title, body }, i) => (
                  <div key={title}>
                    <div className="join-step-top">
                      <Icon size={26} strokeWidth={1.5} />
                      <span>0{i + 1}</span>
                    </div>
                    <h3>{title}</h3>
                    <p>{body}</p>
                  </div>
                ))}
              </div>
              <div className="join-footer">
                <span>Have your certificates ready? Let’s get started.</span>
                <Link className="btn" to="/register">
                  Apply for an account <ArrowUpRight size={17} />
                </Link>
              </div>
            </Reveal>
            <Reveal as="section" className="care-editorial">
              <div>
                <p className="eyebrow">ROOTED IN TANZANIA. FOCUSED ON YOU.</p>
                <h2>
                  Good healthcare starts
                  <br />
                  long before the counter.
                </h2>
              </div>
              <div>
                <p>
                  It starts with having what you need, when you need to make a
                  decision. Kabisa brings your product catalog, business pricing
                  and ordering into one dependable place.
                </p>
                <Link className="text-link" to="/pages/about">
                  Get to know Kabisa <ArrowUpRight size={18} />
                </Link>
              </div>
            </Reveal>
          </>
        )}
        {home?.brands.length ? (
          <Reveal as="section" className="brands-shelf">
            <p className="eyebrow">EXPLORE BRANDS IN OUR CATALOG</p>
            <div>
              {home.brands.slice(0, 6).map((b) => (
                <Link
                  key={b.id}
                  to={approved ? `/catalog?brand=${b.slug}` : "/register"}
                >
                  {b.name}
                </Link>
              ))}
            </div>
          </Reveal>
        ) : null}
        {approved && orders.data?.items.length ? (
          <Reveal as="section" className="store-section">
            <div className="store-section-head">
              <div>
                <p className="eyebrow">KEEP THINGS MOVING</p>
                <h2>Your recent orders</h2>
              </div>
              <Link className="text-link" to="/account/orders">
                Order history <ArrowRight size={16} />
              </Link>
            </div>
            <div className="recent-order-list">
              {orders.data.items.map((order) => (
                <Link key={order.id} to={`/account/orders/${order.id}`}>
                  <Package size={22} />
                  <strong>{order.order_number}</strong>
                  <Badge kind="neutral">
                    {order.status.replaceAll("_", " ")}
                  </Badge>
                  <ArrowUpRight size={18} />
                </Link>
              ))}
            </div>
          </Reveal>
        ) : null}
      </div>
    </div>
  );
}
