import { useQuery } from "@tanstack/react-query";
import { Linking } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import type { Content, Page } from "@kabisa/api-client";
import { api } from "../../src/api";
import { useStore } from "../../src/store";
import {
  Action,
  Empty,
  ErrorView,
  Heading,
  Loading,
  Panel,
  Screen,
  t,
  Txt,
} from "../../src/ui";
export default function PageScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const { config } = useStore();
  const faq = slug === "faqs" || slug === "faq";
  const contact = slug === "contact";
  const query = useQuery({
    queryKey: ["page", slug],
    queryFn: () =>
      api.get<Content & Page<Content>>(faq ? "/faqs" : `/pages/${slug}`),
    enabled: !contact,
  });
  return (
    <Screen
      title={
        contact ? t("page.contact") : faq ? t("page.faq") : query.data?.title
      }
      body={contact ? t("page.contactBody") : undefined}
    >
      <Action
        secondary
        label={t("action.back")}
        onPress={() =>
          router.canGoBack() ? router.back() : router.replace("/")
        }
      />
      {contact ? (
        <>
          {!!String(config?.settings.support_phone || "") && (
            <Action
              secondary
              label={String(config?.settings.support_phone)}
              onPress={() =>
                Linking.openURL("tel:" + String(config?.settings.support_phone))
              }
            />
          )}
          {!!String(config?.settings.support_email || "") && (
            <Action
              secondary
              label={String(config?.settings.support_email)}
              onPress={() =>
                Linking.openURL(
                  "mailto:" + String(config?.settings.support_email),
                )
              }
            />
          )}
          {!!String(config?.settings.support_whatsapp || "") && (
            <Action
              secondary
              label={t("page.whatsapp")}
              onPress={() =>
                Linking.openURL(
                  "https://wa.me/" +
                    String(config?.settings.support_whatsapp).replace(
                      /\D/g,
                      "",
                    ),
                )
              }
            />
          )}
          <Panel>
            <Heading>{config?.company.company_name}</Heading>
            <Txt>{config?.company.company_address}</Txt>
            <Txt muted>{String(config?.settings.business_hours || "")}</Txt>
          </Panel>
          {!config?.settings.support_phone &&
            !config?.settings.support_email && <Txt>{t("page.noContact")}</Txt>}
        </>
      ) : query.isLoading ? (
        <Loading />
      ) : query.isError ? (
        <ErrorView error={query.error} retry={() => void query.refetch()} />
      ) : faq ? (
        query.data?.items.length ? (
          query.data.items.map((f) => (
            <Panel key={f.id}>
              <Heading>{f.question}</Heading>
              <Txt>{plain(f.answer || "")}</Txt>
            </Panel>
          ))
        ) : (
          <Empty title={t("page.faq")} body={t("home.noContent")} />
        )
      ) : (
        <Panel>
          <Txt>{plain(query.data?.body || "")}</Txt>
        </Panel>
      )}
    </Screen>
  );
}
function plain(html: string) {
  return html
    .replace(/<\/(p|h[1-6]|li)>|<br\s*\/?\s*>/gi, "\n\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .trim();
}
