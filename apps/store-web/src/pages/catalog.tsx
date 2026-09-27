import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import type { Page, Product } from "@kabisa/api-client";
import { api } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { t } from "../i18n";
import {
  Empty,
  ErrorState,
  Field,
  PageIntro,
  Skeleton,
} from "../components/ui";
import { ProductCard } from "../components/product-card";
type Option = { id: string; name: string; slug: string };
export default function Catalog() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("search") || "");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const { authenticated } = useStore();
  useSeo(t("nav.catalog"));
  const queryString = params.toString();
  const page = Number(params.get("page") || 1);
  const query = useQuery({
    queryKey: ["products", queryString, authenticated],
    queryFn: async () => {
      try {
        const data = await api.get<Page<Product>>(
          `/catalog/products?${queryString}`,
        );
        if (!authenticated)
          localStorage.setItem(
            "kabisa.catalog-preview",
            JSON.stringify({
              ...data,
              items: data.items.map((p) => ({ ...p, price: null })),
            }),
          );
        return data;
      } catch (error) {
        if (!navigator.onLine && !authenticated) {
          const cache = localStorage.getItem("kabisa.catalog-preview");
          if (cache) return JSON.parse(cache) as Page<Product>;
        }
        throw error;
      }
    },
  });
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.get<Page<Option>>("/catalog/categories"),
  });
  const brands = useQuery({
    queryKey: ["brands"],
    queryFn: () => api.get<Page<Option>>("/catalog/brands"),
  });
  useEffect(() => {
    setSearch(params.get("search") || "");
  }, [params]);
  function filter(key: string, value: string) {
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      next.delete("page");
      if (value) next.set(key, value);
      else next.delete(key);
      return next;
    });
  }
  useEffect(() => {
    if (search === (params.get("search") || "")) return;
    const timer = setTimeout(
      () =>
        setParams((previous) => {
          const next = new URLSearchParams(previous);
          next.delete("page");
          if (search) next.set("search", search);
          else next.delete("search");
          return next;
        }),
      350,
    );
    return () => clearTimeout(timer);
  }, [search, params, setParams]);
  const filterFields = (
    <>
      <div className="filter-heading">
        <h2>{t("catalog.filters")}</h2>
        <button
          className="text-link"
          onClick={() => {
            setSearch("");
            setParams({});
          }}
        >
          {t("action.clear")}
        </button>
      </div>
      <Field label={t("catalog.category")}>
        <select
          value={params.get("category") || ""}
          onChange={(e) => filter("category", e.target.value)}
        >
          <option value="">{t("catalog.all")}</option>
          {categories.data?.items.map((c) => (
            <option key={c.id} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label={t("catalog.brand")}>
        <select
          value={params.get("brand") || ""}
          onChange={(e) => filter("brand", e.target.value)}
        >
          <option value="">{t("catalog.all")}</option>
          {brands.data?.items.map((c) => (
            <option key={c.id} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label={t("catalog.type")}>
        <select
          value={params.get("product_type") || ""}
          onChange={(e) => filter("product_type", e.target.value)}
        >
          <option value="">{t("catalog.all")}</option>
          {[
            "PRESCRIPTION",
            "OTC",
            "SPECIALTY",
            "NUTRACEUTICAL",
            "MEDICAL_DEVICE",
            "CONSUMABLE",
          ].map((c) => (
            <option key={c} value={c}>
              {t(`type.${c}`)}
            </option>
          ))}
        </select>
      </Field>
      <Field label={t("catalog.availability")}>
        <select
          value={params.get("availability") || ""}
          onChange={(e) => filter("availability", e.target.value)}
        >
          <option value="">{t("catalog.all")}</option>
          {["IN_STOCK", "LIMITED", "OUT_OF_STOCK"].map((c) => (
            <option key={c} value={c}>
              {t(`status.${c}`)}
            </option>
          ))}
        </select>
      </Field>
      <label className="check-label">
        <input
          type="checkbox"
          checked={params.get("prescription") === "true"}
          onChange={(e) =>
            filter("prescription", e.target.checked ? "true" : "")
          }
        />
        {t("catalog.prescription")}
      </label>
      {authenticated && (
        <div className="price-filter">
          <Field label={t("catalog.minPrice")}>
            <input
              type="number"
              min="0"
              value={params.get("min_price") || ""}
              onChange={(e) => filter("min_price", e.target.value)}
            />
          </Field>
          <Field label={t("catalog.maxPrice")}>
            <input
              type="number"
              min="0"
              value={params.get("max_price") || ""}
              onChange={(e) => filter("max_price", e.target.value)}
            />
          </Field>
        </div>
      )}
    </>
  );
  return (
    <div className="container catalog-page">
      <PageIntro
        eyebrow={t("nav.catalog")}
        title={t("catalog.title")}
        body={t("catalog.subtitle")}
      />
      <div className="catalog-toolbar">
        <div className="search-field">
          <Search size={19} />
          <input
            aria-label={t("nav.search")}
            placeholder={t("nav.search")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              aria-label={t("action.clear")}
            >
              <X size={17} />
            </button>
          )}
        </div>
        <button
          className="btn secondary filter-toggle"
          onClick={() => setFiltersOpen(!filtersOpen)}
          aria-expanded={filtersOpen}
        >
          <SlidersHorizontal size={17} />
          {t("catalog.filters")}
        </button>
        <label className="sort-label">
          <span>{t("catalog.sort")}</span>
          <select
            aria-label={t("catalog.sort")}
            value={params.get("sort") || "featured"}
            onChange={(e) => filter("sort", e.target.value)}
          >
            {[
              ["featured", "catalog.featured"],
              ["newest", "catalog.newest"],
              ["name", "catalog.name"],
              ...(authenticated
                ? [
                    ["price_asc", "catalog.lowPrice"],
                    ["price_desc", "catalog.highPrice"],
                  ]
                : []),
            ].map(([value, key]) => (
              <option value={value} key={value}>
                {t(key)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="catalog-layout">
        <aside className={`catalog-filters ${filtersOpen ? "open" : ""}`}>
          {filterFields}
        </aside>
        <div className="catalog-results">
          <div className="results-meta">
            <p>
              <strong>{query.data?.total ?? "—"}</strong>{" "}
              {t("catalog.products")}
            </p>
            {query.isFetching && !query.isLoading && (
              <span className="loading-dot" />
            )}
          </div>
          {!navigator.onLine && (
            <p className="inline-notice">{t("error.offlineCatalog")}</p>
          )}
          {query.isLoading ? (
            <Skeleton cards={6} />
          ) : query.isError ? (
            <ErrorState error={query.error} retry={() => query.refetch()} />
          ) : query.data?.items.length ? (
            <>
              <div className="product-grid catalog-grid">
                {query.data.items.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
              <div className="pagination">
                <button
                  className="btn secondary"
                  disabled={page <= 1}
                  onClick={() =>
                    setParams((previous) => {
                      const next = new URLSearchParams(previous);
                      next.set("page", String(page - 1));
                      return next;
                    })
                  }
                >
                  <ArrowLeft size={15} />
                  {t("catalog.previous")}
                </button>
                <span>
                  {t("catalog.page")} {page} {t("catalog.of")}{" "}
                  {Math.max(1, Math.ceil(query.data.total / 24))}
                </span>
                <button
                  className="btn secondary"
                  disabled={page * 24 >= query.data.total}
                  onClick={() =>
                    setParams((previous) => {
                      const next = new URLSearchParams(previous);
                      next.set("page", String(page + 1));
                      return next;
                    })
                  }
                >
                  {t("catalog.next")}
                  <ArrowRight size={15} />
                </button>
              </div>
            </>
          ) : (
            <Empty
              title={t("catalog.noResults")}
              body={t("catalog.noResultsBody")}
              action={
                <button className="btn secondary" onClick={() => setParams({})}>
                  {t("action.clear")}
                </button>
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}
