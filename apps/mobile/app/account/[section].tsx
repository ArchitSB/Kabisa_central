import { useState } from "react";
import { formatMoney } from "@kabisa/core";
import { View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import type { Address, Content, Page, Product } from "@kabisa/api-client";
import { api, download, pickUpload, queryClient, tokens } from "../../src/api";
import { AddressForm } from "../../src/forms";
import { OrdersList } from "../../src/orders";
import { useStore } from "../../src/store";
import {
  Action,
  Badge,
  Empty,
  ErrorView,
  Heading,
  Input,
  Loading,
  Panel,
  ProductCard,
  RequireLogin,
  Screen,
  s,
  t,
  Txt,
} from "../../src/ui";
export default function Section() {
  const { section } = useLocalSearchParams<{ section: string }>();
  return (
    <RequireLogin>
      <Screen title={t(`account.${section}`)}>
        <Action
          secondary
          label={t("action.back")}
          onPress={() => router.replace("/account")}
        />
        {section === "orders" ? (
          <OrdersList />
        ) : section === "verification" ? (
          <Verification />
        ) : section === "addresses" ? (
          <Addresses />
        ) : section === "favourites" ? (
          <Favourites />
        ) : section === "templates" ? (
          <Templates />
        ) : section === "notifications" ? (
          <Notifications />
        ) : section === "security" ? (
          <Security />
        ) : (
          <Profile />
        )}
      </Screen>
    </RequireLogin>
  );
}
function Profile() {
  const { customer, refresh, config } = useStore();
  const [name, setName] = useState(customer?.full_name || "");
  return (
    <>
      <Panel>
        <Heading>{customer?.customer.business_name}</Heading>
        <Txt>{customer?.customer.physical_address}</Txt>
        <Txt muted>
          {customer?.phone} · {customer?.email}
        </Txt>
        <Txt>
          {t("account.paymentTerms")}: {customer?.customer.payment_terms}
        </Txt>
        {customer?.customer.payment_terms === "CREDIT" && (
          <Txt>
            {t("order.balance")}:{" "}
            {formatMoney(
              customer.customer.credit_balance,
              config?.currency || "TZS",
            )}
          </Txt>
        )}
        {customer?.customer.payment_terms === "CREDIT" && (
          <Txt>
            {t("account.creditLimit")}:{" "}
            {customer.customer.credit_limit
              ? formatMoney(
                  customer.customer.credit_limit,
                  config?.currency || "TZS",
                )
              : "—"}
          </Txt>
        )}
      </Panel>
      <Panel>
        <Input
          label={t("auth.fullName")}
          value={name}
          onChangeText={setName}
          maxLength={150}
        />
        <Action
          label={t("action.save")}
          disabled={name.trim().length < 2}
          onPress={async () => {
            await api.patch("/me", { full_name: name });
            await refresh();
          }}
        />
      </Panel>
    </>
  );
}
function Verification() {
  const { customer, config, refresh } = useStore();
  if (!customer) return <Loading />;
  return (
    <>
      <Panel>
        <Badge status={customer.customer.status} />
        <Txt>
          {
            (
              config?.settings.verification_messages as Record<string, string>
            )?.[customer.customer.status]
          }
        </Txt>
        {customer.customer.rejection_reason && (
          <Txt>{customer.customer.rejection_reason}</Txt>
        )}
        <Txt muted>{t("account.documentsBody")}</Txt>
      </Panel>
      {["TIN", "TMDA", "PHARMACY_COUNCIL", "TBS", "OTHER"].map((type) => {
        const document = customer.documents.find((d) => d.doc_type === type);
        return (
          <Panel key={type}>
            <Heading>{t(`account.doc.${type}`)}</Heading>
            <Txt muted>
              {document?.original_filename || t("account.missing")}
            </Txt>
            {document && (
              <>
                <Badge status={document.status} />
                {document.notes && <Txt>{document.notes}</Txt>}
                <Action
                  secondary
                  label={t("action.download")}
                  onPress={() =>
                    download(
                      `/documents/${document.id}/download`,
                      document.original_filename,
                    )
                  }
                />
              </>
            )}
            <Action
              secondary
              label={t("account.upload")}
              icon="document-attach-outline"
              onPress={async () => {
                const uploaded = await pickUpload("/documents", {
                  doc_type: type,
                });
                if (uploaded) await refresh();
              }}
            />
          </Panel>
        );
      })}
      {["PENDING", "REJECTED"].includes(customer.customer.status) && (
        <Action
          label={t("account.submitReview")}
          disabled={!!customer.missing_documents.length}
          onPress={async () => {
            await api.post("/verification/submit");
            await refresh();
          }}
        />
      )}
    </>
  );
}
function Addresses() {
  const query = useQuery({
    queryKey: ["addresses"],
    queryFn: () => api.get<Page<Address>>("/addresses"),
  });
  const [form, setForm] = useState(false);
  const [editing, setEditing] = useState<Address>();
  return (
    <>
      <Action
        secondary
        label={t("address.add")}
        onPress={() => {
          setEditing(undefined);
          setForm(!form);
        }}
      />
      {form && (
        <Panel>
          <AddressForm
            key={editing?.id || "new"}
            initial={editing}
            onSaved={() => setForm(false)}
          />
        </Panel>
      )}
      {query.isLoading ? (
        <Loading />
      ) : query.isError ? (
        <ErrorView error={query.error} />
      ) : query.data?.items.length ? (
        query.data.items.map((a) => (
          <Panel key={a.id}>
            <Heading>{a.label}</Heading>
            {a.is_default && <Txt muted>{t("address.defaultBadge")}</Txt>}
            <Txt>
              {a.address}, {a.region}
            </Txt>
            <Txt muted>
              {a.contact_person} {a.phone}
            </Txt>
            <Action
              secondary
              label={t("action.edit")}
              onPress={() => {
                setEditing(a);
                setForm(true);
              }}
            />
            <Action
              secondary
              label={t("action.remove")}
              onPress={async () => {
                await api.delete(`/addresses/${a.id}`);
                await query.refetch();
              }}
            />
          </Panel>
        ))
      ) : (
        !form && (
          <Empty title={t("address.empty")} body={t("address.emptyBody")} />
        )
      )}
    </>
  );
}
function Favourites() {
  const query = useQuery({
    queryKey: ["favourites"],
    queryFn: () => api.get<Page<Product>>("/favourites"),
  });
  return query.isLoading ? (
    <Loading />
  ) : query.isError ? (
    <ErrorView error={query.error} />
  ) : query.data?.items.length ? (
    <View style={s.productGrid}>
      {query.data.items.map((p) => (
        <View key={p.id} style={{ width: "100%", gap: 12 }}>
          <ProductCard product={p} />
          <Action
            secondary
            label={t("action.remove")}
            onPress={async () => {
              await api.delete(`/favourites/${p.id}`);
              await query.refetch();
            }}
          />
        </View>
      ))}
    </View>
  ) : (
    <Empty
      title={t("account.noFavourites")}
      body={t("account.noFavouritesBody")}
    />
  );
}
function Templates() {
  const { refresh } = useStore();
  const query = useQuery({
    queryKey: ["templates"],
    queryFn: () =>
      api.get<
        Page<{
          id: string;
          name: string;
          items: { product_id: string; quantity: number; name: string }[];
        }>
      >("/templates"),
  });
  return query.isLoading ? (
    <Loading />
  ) : query.isError ? (
    <ErrorView error={query.error} />
  ) : query.data?.items.length ? (
    <>
      {query.data.items.map((item) => (
        <Panel key={item.id}>
          <Heading>{item.name}</Heading>
          {item.items.map((i) => (
            <Txt key={i.product_id}>
              {i.quantity} × {i.name}
            </Txt>
          ))}
          <Action
            label={t("account.addTemplate")}
            onPress={async () => {
              await api.post(`/templates/${item.id}/add-to-cart`);
              await refresh();
              router.push("/cart");
            }}
          />
          <Action
            secondary
            label={t("action.delete")}
            onPress={async () => {
              await api.delete(`/templates/${item.id}`);
              await query.refetch();
            }}
          />
        </Panel>
      ))}
    </>
  ) : (
    <Empty
      title={t("account.noTemplates")}
      body={t("account.noTemplatesBody")}
    />
  );
}
function Notifications() {
  const query = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<Page<Content>>("/notifications"),
  });
  return query.isLoading ? (
    <Loading />
  ) : query.isError ? (
    <ErrorView error={query.error} />
  ) : query.data?.items.length ? (
    <>
      {query.data.items.map((n) => (
        <Panel key={n.id}>
          <Heading>{n.title}</Heading>
          <Txt>{n.body}</Txt>
          <Txt muted small>
            {new Date(String(n.created_at)).toLocaleString()}
          </Txt>
          {!n.read_at && (
            <Action
              secondary
              label={t("account.markRead")}
              onPress={async () => {
                await api.post(`/notifications/${n.id}/read`);
                await query.refetch();
              }}
            />
          )}
          {typeof (n.payload as { order_id?: string })?.order_id ===
            "string" && (
            <Action
              secondary
              label={t("order.detail")}
              onPress={() =>
                router.push(
                  `/orders/${(n.payload as { order_id: string }).order_id}`,
                )
              }
            />
          )}
        </Panel>
      ))}
    </>
  ) : (
    <Empty
      title={t("account.noNotifications")}
      body={t("account.noNotificationsBody")}
    />
  );
}
function Security() {
  const [old, setOld] = useState("");
  const [password, setPassword] = useState("");
  const query = useQuery({
    queryKey: ["sessions"],
    queryFn: () =>
      api.get<
        Page<{
          id: string;
          current: boolean;
          device_label: string;
          created_at: string;
        }>
      >("/auth/sessions"),
  });
  async function clear() {
    await tokens.set(null);
    queryClient.clear();
    router.replace("/login");
  }
  return (
    <>
      <Panel>
        <Heading>{t("account.changePassword")}</Heading>
        <Input
          label={t("account.currentPassword")}
          value={old}
          onChangeText={setOld}
          secureTextEntry
          autoComplete="current-password"
        />
        <Input
          label={t("auth.newPassword")}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="new-password"
          maxLength={72}
        />
        <Action
          label={t("account.changePassword")}
          disabled={!old || password.length < 8}
          onPress={async () => {
            await api.post("/auth/password/change", {
              current_password: old,
              password,
            });
            await clear();
          }}
        />
      </Panel>
      <Heading>{t("account.devices")}</Heading>
      {query.isError ? (
        <ErrorView error={query.error} />
      ) : (
        query.data?.items.map((session) => (
          <Panel key={session.id}>
            <Txt>{session.device_label}</Txt>
            {session.current && <Txt muted>{t("account.currentDevice")}</Txt>}
            <Txt muted small>
              {new Date(session.created_at).toLocaleString()}
            </Txt>
            <Action
              secondary
              label={t("account.revoke")}
              onPress={async () => {
                await api.delete(`/auth/sessions/${session.id}`);
                if (session.current) await clear();
                else await query.refetch();
              }}
            />
          </Panel>
        ))
      )}
      <Action
        secondary
        label={t("account.signOutAll")}
        onPress={async () => {
          await api.post("/auth/logout-all");
          await clear();
        }}
      />
    </>
  );
}
