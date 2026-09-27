import { Heart, Pill, Plus, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import type { Product } from "@kabisa/api-client";
import { formatMoney } from "@kabisa/core";
import { t } from "../i18n";
import { api, assetUrl, queryClient } from "../lib/api";
import { useStore } from "../lib/store";
import { AsyncButton, Badge } from "./ui";
export function ProductImage({
  product,
  eager = false,
}: {
  product: Product;
  eager?: boolean;
}) {
  const src = assetUrl(product.images[0]);
  return (
    <div className={`product-image type-${product.product_type.toLowerCase()}`}>
      {src ? (
        <img
          src={src}
          alt={product.name}
          loading={eager ? "eager" : "lazy"}
          decoding="async"
          onError={(e) => {
            e.currentTarget.style.display = "none";
            e.currentTarget.parentElement?.classList.add("image-missing");
          }}
        />
      ) : null}
      <div
        className={`product-placeholder ${src ? "with-image" : ""}`}
        aria-label={t("product.noImage")}
      >
        <Pill size={52} strokeWidth={1} />
        <span>{product.strength || product.unit}</span>
      </div>
    </div>
  );
}
export function ProductCard({ product }: { product: Product }) {
  const { add, authenticated, config } = useStore();
  return (
    <article className="product-card">
      <div className="product-visual">
        <Link to={`/product/${product.slug}`} tabIndex={-1} aria-hidden="true">
          <ProductImage product={product} />
        </Link>
        {product.requires_prescription && <span className="pom-tag">Rx</span>}
        {authenticated && config?.settings.enable_wishlist && (
          <AsyncButton
            className="favourite-button"
            action={async () => {
              await api.post(`/favourites/${product.id}`);
              await queryClient.invalidateQueries({ queryKey: ["favourites"] });
            }}
          >
            <Heart size={17} />
            <span className="sr-only">{t("product.favourite")}</span>
          </AsyncButton>
        )}
      </div>
      <div className="product-info">
        <p className="product-brand">
          {product.brand?.name ?? product.category.name}
        </p>
        <Link to={`/product/${product.slug}`}>
          <h3>{product.name}</h3>
        </Link>
        <p className="product-pack">
          {[product.strength, product.pack_size].filter(Boolean).join(" · ") ||
            product.unit}
        </p>
        <Badge
          kind={
            product.availability === "IN_STOCK"
              ? "success"
              : product.availability === "LIMITED"
                ? "warning"
                : "neutral"
          }
        >
          {t(`status.${product.availability}`)}
        </Badge>
        <div className="product-bottom">
          {product.price !== null ? (
            <div>
              <strong>{formatMoney(product.price, product.currency)}</strong>
              <span>{t("product.unitPrice")}</span>
            </div>
          ) : authenticated ? (
            <span className="muted small">{t("product.priceUnavailable")}</span>
          ) : (
            <Link className="price-link" to="/login">
              {t("product.priceHidden")}
            </Link>
          )}
          <AsyncButton
            className="add-button"
            action={() => add(product)}
            disabled={product.availability === "OUT_OF_STOCK"}
          >
            <Plus size={20} />
            <span className="sr-only">{t("action.add")}</span>
          </AsyncButton>
        </div>
      </div>
      <span className="sr-only">
        <ShieldCheck />
        {t("product.verified")}
      </span>
    </article>
  );
}
