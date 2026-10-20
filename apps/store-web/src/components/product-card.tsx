import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import {
  Heart,
  Check,
  Pill,
  Plus,
  ShieldCheck,
  Stethoscope,
  Package,
  Leaf,
} from "lucide-react";
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
  const Icon =
    product.product_type === "MEDICAL_DEVICE"
      ? Stethoscope
      : product.product_type === "CONSUMABLE"
        ? Package
        : product.product_type === "NUTRACEUTICAL"
          ? Leaf
          : Pill;
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
        <Icon size={46} strokeWidth={1} />
        <span>{product.strength || product.pack_size || product.unit}</span>
        <small>Product image coming soon</small>
      </div>
    </div>
  );
}
export function ProductCard({ product }: { product: Product }) {
  const { add, authenticated, config } = useStore();
  const reduced = useReducedMotion();
  const [added, setAdded] = useState(false);
  useEffect(() => {
    if (!added) return;
    const timer = setTimeout(() => setAdded(false), 1400);
    return () => clearTimeout(timer);
  }, [added]);
  return (
    <motion.article
      className="product-card"
      initial={false}
      whileHover={reduced ? undefined : { y: -3 }}
      transition={{ duration: 0.2, ease: [0.2, 0, 0, 1] }}
    >
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
        {product.sku.startsWith("DEMO-") && product.images.length > 0 && (
          <span className="product-illustration-label">Illustrative image</span>
        )}
      </div>
      <div className="product-info">
        <p className="product-brand">
          {product.brand?.name ?? product.category.name}
        </p>
        <Link to={`/product/${product.slug}`}>
          <h3>{product.name}</h3>
        </Link>
        <span className="product-sku">{product.sku}</span>
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
            className={`add-button ${added ? "just-added" : ""}`}
            action={async () => {
              await add(product);
              setAdded(true);
            }}
            disabled={product.availability === "OUT_OF_STOCK"}
          >
            {added ? <Check size={20} /> : <Plus size={20} />}
            <span className="sr-only">
              {t("action.add")} {product.name}
            </span>
          </AsyncButton>
        </div>
      </div>
      <span role="status" className="sr-only">
        {added ? `${product.name} added to your basket.` : ""}
      </span>
      <span className="sr-only">
        <ShieldCheck />
        {t("product.verified")}
      </span>
    </motion.article>
  );
}
