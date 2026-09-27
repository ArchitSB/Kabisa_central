import { useEffect } from "react";
import { useStore } from "./store";
export function useSeo(
  title?: string,
  description?: string,
  data?: Record<string, unknown>,
) {
  const { config } = useStore();
  const base = String(config?.settings.seo_title || "Kabisa");
  const desc = description || String(config?.settings.seo_description || "");
  const json = data ? JSON.stringify(data) : "";
  useEffect(() => {
    document.title = title ? `${title} | ${base}` : base;
    const set = (key: string, content: string, property = false) => {
      let element = document.querySelector<HTMLMetaElement>(
        `meta[${property ? "property" : "name"}="${key}"]`,
      );
      if (!element) {
        element = document.createElement("meta");
        element.setAttribute(property ? "property" : "name", key);
        document.head.appendChild(element);
      }
      element.content = content;
    };
    set("description", desc);
    set("og:title", document.title, true);
    set("og:description", desc, true);
    set("og:url", location.href, true);
    set("og:type", "website", true);
    set("og:image", String(config?.settings.seo_og_image || ""), true);
    let script = document.querySelector<HTMLScriptElement>("#page-jsonld");
    if (!script) {
      script = document.createElement("script");
      script.id = "page-jsonld";
      script.type = "application/ld+json";
      document.head.appendChild(script);
    }
    script.textContent =
      json ||
      JSON.stringify({
        "@context": "https://schema.org",
        "@type": "Organization",
        name: config?.company.company_name || base,
        url: location.origin,
      });
    return () => {
      script?.remove();
    };
  }, [
    base,
    title,
    desc,
    json,
    config?.company.company_name,
    config?.settings.seo_og_image,
  ]);
}
