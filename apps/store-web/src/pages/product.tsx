import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, FileCheck2, ShieldCheck, ShoppingBag } from "lucide-react";
import type { Product } from "@kabisa/api-client";
import { formatMoney } from "@kabisa/core";
import { api } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { t } from "../i18n";
import {
  AsyncButton,
  Badge,
  ErrorState,
  Quantity,
  SectionHeading,
  Skeleton,
  TrustNote,
} from "../components/ui";
import { ProductCard, ProductImage } from "../components/product-card";
export default function ProductDetail() {
  const { slug } = useParams();
  const { authenticated, add } = useStore();
  const [quantity, setQuantity] = useState(1);
  const query = useQuery({
    queryKey: ["product", slug, authenticated],
    queryFn: () =>
      api.get<Product & { related: Product[] }>(`/catalog/products/${slug}`),
  });
  const p = query.data;
  useSeo(
    p?.name,
    p?.description || undefined,
    p
      ? {
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "Product",
              name: p.name,
              sku: p.sku,
              description: p.description,
              image: p.images,
              brand: p.brand
                ? { "@type": "Brand", name: p.brand.name }
                : undefined,
              offers: p.price
                ? {
                    "@type": "Offer",
                    price: p.price,
                    priceCurrency: p.currency,
                    availability: `https://schema.org/${p.availability === "OUT_OF_STOCK" ? "OutOfStock" : "InStock"}`,
                    url: location.href,
                  }
                : undefined,
            },
            {
              "@type": "BreadcrumbList",
              itemListElement: [
                {
                  "@type": "ListItem",
                  position: 1,
                  name: t("nav.catalog"),
                  item: location.origin + "/catalog",
                },
                {
                  "@type": "ListItem",
                  position: 2,
                  name: p.category.name,
                  item:
                    location.origin +
                    "/catalog?category=" +
                    encodeURIComponent(p.category.slug),
                },
                {
                  "@type": "ListItem",
                  position: 3,
                  name: p.name,
                  item: location.href,
                },
              ],
            },
          ],
        }
      : undefined,
  );
  if (query.isLoading)
    return (
      <div className="container section">
        <Skeleton cards={2} />
      </div>
    );
  if (query.isError || !p)
    return (
      <div className="container">
        <ErrorState error={query.error} />
      </div>
    );
  return (
    <div className="container product-page">
      <nav className="breadcrumbs">
        <Link to="/catalog">{t("nav.catalog")}</Link>
        <span>/</span>
        <Link to={`/catalog?category=${p.category.slug}`}>
          {p.category.name}
        </Link>
        <span>/</span>
        <span>{p.name}</span>
      </nav>
      <section className="product-detail-grid">
        <div className="detail-visual">
          <ProductImage product={p} eager />
          {p.requires_prescription && (
            <span className="detail-rx">Rx · {t("product.pom")}</span>
          )}
        </div>
        <div className="detail-copy">
          <p className="eyebrow">{p.brand?.name || p.category.name}</p>
          <h1>{p.name}</h1>
          <p className="detail-pack">
            {[p.generic_name, p.strength, p.pack_size]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <Badge
            kind={
              p.availability === "IN_STOCK"
                ? "success"
                : p.availability === "LIMITED"
                  ? "warning"
                  : "neutral"
            }
          >
            {t(`status.${p.availability}`)}
          </Badge>
          <div className="detail-price">
            {p.price !== null ? (
              <>
                <span>{t("product.exclusive")}</span>
                <strong>{formatMoney(p.price, p.currency)}</strong>
                <small>{t("product.unitPrice")}</small>
              </>
            ) : (
              <>
                <p>{t("product.loginPrompt")}</p>
                <Link className="text-link" to="/login">
                  {t("nav.login")}
                  <ArrowRight size={16} />
                </Link>
              </>
            )}
          </div>
          <div className="detail-actions">
            <Quantity value={quantity} onChange={setQuantity} />
            <AsyncButton
              action={() => add(p, quantity)}
              disabled={p.availability === "OUT_OF_STOCK"}
            >
              <ShoppingBag size={18} />
              {t("action.add")}
            </AsyncButton>
          </div>
          {p.requires_prescription && (
            <div className="prescription-note">
              <FileCheck2 size={22} />
              <div>
                <strong>{t("product.pom")}</strong>
                <p>{t("product.pomBody")}</p>
              </div>
            </div>
          )}
          {p.registration_no && (
            <TrustNote>
              <span>
                {t("product.registration")}:{" "}
                <strong>{p.registration_no}</strong>
              </span>
            </TrustNote>
          )}
          <TrustNote>{t("product.verified")}</TrustNote>
          <dl className="product-specs">
            {[
              ["product.sku", p.sku],
              ["product.brand", p.brand?.name],
              ["product.generic", p.generic_name],
              ["product.strength", p.strength],
              ["product.pack", p.pack_size],
              ["product.unit", p.unit],
            ]
              .filter(([, value]) => value)
              .map(([key, value]) => (
                <div key={key}>
                  <dt>{t(key!)}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
          </dl>
        </div>
      </section>
      {p.description && (
        <section className="product-description">
          <h2>{t("product.description")}</h2>
          <p>{p.description}</p>
        </section>
      )}
      {p.related.length > 0 && (
        <section className="section">
          <SectionHeading
            title={t("product.related")}
            to={`/catalog?category=${p.category.slug}`}
          />
          <div className="product-grid">
            {p.related.map((product) => (
              <ProductCard product={product} key={product.id} />
            ))}
          </div>
        </section>
      )}
      <div className="product-safe-note">
        <ShieldCheck size={18} />
        <span>{t("cart.livePrices")}</span>
      </div>
    </div>
  );
}
