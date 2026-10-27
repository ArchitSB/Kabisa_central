import { Link, useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import DOMPurify from "dompurify";
import {
  ArrowRight,
  ArrowUpRight,
  Clock3,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  Plus,
} from "lucide-react";
import type { Content, Page } from "@kabisa/api-client";
import { api } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { t } from "../i18n";
import { Empty, ErrorState, PageIntro, Skeleton } from "../components/ui";
export default function ContentPage() {
  const { slug } = useParams();
  const location = useLocation();
  const isFAQ = location.pathname === "/faq";
  const isContact = location.pathname === "/contact";
  const { config } = useStore();
  const query = useQuery({
    queryKey: ["page", slug, isFAQ],
    queryFn: () =>
      api.get<Content | Page<Content>>(isFAQ ? "/faqs" : `/pages/${slug}`),
    enabled: !isContact && !!(isFAQ || slug),
  });
  const page = query.data as Content | undefined;
  useSeo(isFAQ ? t("page.faq") : isContact ? t("page.contact") : page?.title);
  const cfg = config?.settings;
  return (
    <div className="container content-page">
      {isContact ? (
        <>
          <PageIntro
            eyebrow={t("nav.support")}
            title={t("page.contact")}
            body={t("page.contactBody")}
          />
          <div className="contact-grid">
            {[
              {
                key: "support_phone",
                title: "page.phone",
                icon: Phone,
                prefix: "tel:",
              },
              {
                key: "support_email",
                title: "page.email",
                icon: Mail,
                prefix: "mailto:",
              },
              {
                key: "support_whatsapp",
                title: "page.whatsapp",
                icon: MessageCircle,
                prefix: "https://wa.me/",
              },
            ].map(({ key, title, icon: Icon, prefix }) =>
              cfg?.[key] ? (
                <a
                  className="panel contact-card"
                  key={key}
                  href={
                    prefix +
                    (key === "support_whatsapp"
                      ? String(cfg[key]).replace(/\D/g, "")
                      : String(cfg[key]))
                  }
                >
                  <Icon size={28} strokeWidth={1.3} />
                  <h2>{t(title)}</h2>
                  <p>{String(cfg[key])}</p>
                  <ArrowUpRight size={20} />
                </a>
              ) : null,
            )}
            {config?.company.company_address && (
              <section className="panel contact-card">
                <MapPin size={28} strokeWidth={1.3} />
                <h2>{t("page.location")}</h2>
                <p>{config.company.company_address}</p>
              </section>
            )}
            {cfg?.business_hours && (
              <section className="panel contact-card">
                <Clock3 size={28} strokeWidth={1.3} />
                <h2>{t("page.hours")}</h2>
                <p>{String(cfg.business_hours)}</p>
              </section>
            )}
          </div>
          {!cfg?.support_phone &&
            !cfg?.support_email &&
            !cfg?.support_whatsapp && (
              <p className="muted">{t("page.noContact")}</p>
            )}
        </>
      ) : query.isLoading ? (
        <Skeleton cards={2} />
      ) : query.isError && query.data === undefined ? (
        <ErrorState error={query.error} retry={() => query.refetch()} />
      ) : isFAQ ? (
        <>
          <PageIntro
            eyebrow={t("nav.support")}
            title={t("page.faq")}
            body={t("page.faqSubtitle")}
          />
          <div className="faq-list">
            {(query.data as Page<Content>)?.items.map((item) => (
              <details key={item.id}>
                <summary>
                  {item.question}
                  <Plus size={20} />
                </summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </>
      ) : page ? (
        <article>
          <PageIntro eyebrow={t("page.updated")} title={page.title || ""} />
          {page.body?.includes("<") ? (
            <div
              className="prose"
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(page.body, {
                  ALLOWED_TAGS: [
                    "p",
                    "h2",
                    "h3",
                    "ul",
                    "ol",
                    "li",
                    "strong",
                    "em",
                    "a",
                    "br",
                    "blockquote",
                  ],
                  ALLOWED_ATTR: ["href", "title"],
                }),
              }}
            />
          ) : (
            <div className="prose">
              {page.body?.split("\n\n").map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          )}
          <Link className="text-link" to="/contact">
            {t("nav.support")}
            <ArrowRight size={17} />
          </Link>
        </article>
      ) : null}
    </div>
  );
}
export function NotFound() {
  return (
    <div className="container">
      <Empty
        title={t("page.notFound")}
        body={t("page.notFoundBody")}
        action={
          <Link className="btn" to="/">
            {t("page.backHome")}
          </Link>
        }
      />
    </div>
  );
}
