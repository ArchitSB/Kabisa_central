import { useState, type FormEvent } from "react";
import {
  Link,
  NavLink,
  Navigate,
  useNavigate,
  useParams,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Bell,
  Bookmark,
  Check,
  ChevronRight,
  Download,
  FileCheck2,
  Heart,
  LayoutDashboard,
  LogOut,
  MapPin,
  MonitorSmartphone,
  Package,
  Plus,
  ShieldCheck,
  Trash2,
  UserRound,
} from "lucide-react";
import type { Address, Content, Page, Product } from "@kabisa/api-client";
import { formatMoney } from "@kabisa/core";
import { toast } from "sonner";
import { api, download, queryClient, tokenStore, upload } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { label, t } from "../i18n";
import { AddressForm } from "../components/address-form";
import { ProductCard } from "../components/product-card";
import {
  AsyncButton,
  Badge,
  Empty,
  ErrorState,
  Field,
  PageIntro,
  Skeleton,
} from "../components/ui";
import { OrdersList } from "./orders";
const tabs = [
  { id: "", key: "overview", icon: LayoutDashboard },
  { id: "orders", key: "orders", icon: Package },
  { id: "verification", key: "verification", icon: ShieldCheck },
  { id: "addresses", key: "addresses", icon: MapPin },
  { id: "favourites", key: "favourites", icon: Heart },
  { id: "templates", key: "templates", icon: Bookmark },
  { id: "notifications", key: "notifications", icon: Bell },
  { id: "security", key: "security", icon: MonitorSmartphone },
];
export default function Account() {
  const { section = "" } = useParams();
  const { customer, loading, logout, config, refresh, error } = useStore();
  const navigate = useNavigate();
  useSeo(
    t(`account.${tabs.find((tab) => tab.id === section)?.key || "overview"}`),
  );
  if (loading)
    return (
      <div className="container section">
        <Skeleton cards={2} />
      </div>
    );
  if (!customer)
    return (
      <div className="container">
        <ErrorState error={error} retry={() => refresh()} />
      </div>
    );
  const business = customer.customer;
  const approved = business.status === "VERIFIED";
  if (
    !approved &&
    !["verification", "notifications", "security", ""].includes(section)
  )
    return <Navigate to="/account/verification" replace />;
  const messages = config?.settings.verification_messages as
    Record<string, string> | undefined;
  return (
    <div className="container account-page">
      <PageIntro
        eyebrow={business.business_name}
        title={
          approved
            ? "Your account, all together."
            : "Your next step starts here."
        }
        body={
          approved
            ? "Business details, orders and support. Just where you need them."
            : "Complete your application. We’ll take care of the review."
        }
      />
      <div className="account-layout">
        <aside className="account-sidebar">
          <div className="account-identity">
            <span>
              {customer.full_name
                .split(" ")
                .map((v) => v[0])
                .slice(0, 2)
                .join("")}
            </span>
            <div>
              <strong>{customer.full_name}</strong>
              <Badge
                kind={business.status === "VERIFIED" ? "success" : "warning"}
              >
                {label(business.status)}
              </Badge>
            </div>
          </div>
          <nav>
            {tabs
              .filter(
                (tab) =>
                  approved ||
                  ["", "verification", "notifications", "security"].includes(
                    tab.id,
                  ),
              )
              .map(({ id, key, icon: Icon }) => (
                <NavLink end to={`/account${id ? "/" + id : ""}`} key={key}>
                  <Icon size={18} />
                  {t(`account.${key}`)}
                  <ChevronRight size={14} />
                </NavLink>
              ))}
            <AsyncButton
              className="account-logout"
              action={async () => {
                await logout();
                navigate("/");
              }}
            >
              <LogOut size={18} />
              {t("action.signOut")}
            </AsyncButton>
          </nav>
        </aside>
        <div className="account-content">
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
            <>
              <section
                className={`verification-banner ${business.status === "VERIFIED" ? "verified" : ""}`}
              >
                <ShieldCheck size={30} strokeWidth={1.4} />
                <div>
                  <strong>{label(business.status)}</strong>
                  <p>{messages?.[business.status]}</p>
                </div>
                <Link to="/account/verification">
                  <ArrowRight size={19} />
                  <span className="sr-only">{t("account.verification")}</span>
                </Link>
              </section>
              <div className="account-shortcuts">
                {tabs
                  .filter((tab) =>
                    approved
                      ? ["orders", "verification", "addresses"].includes(tab.id)
                      : ["verification", "notifications", "security"].includes(
                          tab.id,
                        ),
                  )
                  .map(({ id, key, icon: Icon }) => (
                    <Link className="panel" key={id} to={`/account/${id}`}>
                      <Icon size={24} strokeWidth={1.4} />
                      <span>{t(`account.${key}`)}</span>
                      <ArrowRight size={17} />
                    </Link>
                  ))}
              </div>
              <section className="panel">
                <h2>{t("account.business")}</h2>
                <dl className="profile-details">
                  {[
                    ["auth.businessName", business.business_name],
                    [
                      "auth.businessType",
                      t(`business.${business.business_type}`),
                    ],
                    ["auth.physicalAddress", business.physical_address],
                    ["auth.region", business.region],
                    ["account.tier", business.price_tier],
                    ["auth.phone", customer.phone],
                    ["auth.email", customer.email],
                  ].map(([key, value]) => (
                    <div key={key}>
                      <dt>{t(key!)}</dt>
                      <dd>{value || "—"}</dd>
                    </div>
                  ))}
                </dl>
              </section>
              <ProfileForm />
              {business.payment_terms === "CREDIT" && (
                <section className="panel credit-card">
                  <h2>{t("account.credit")}</h2>
                  <p>{t("order.balance")}</p>
                  <strong>
                    {formatMoney(
                      business.credit_balance,
                      config?.currency || "TZS",
                    )}
                  </strong>
                  <p>{t("account.creditLimit")}</p>
                  <strong>
                    {business.credit_limit
                      ? formatMoney(
                          business.credit_limit,
                          config?.currency || "TZS",
                        )
                      : "—"}
                  </strong>
                  <Link className="text-link" to="/account/orders">
                    {t("account.orders")}
                    <ArrowRight size={17} />
                  </Link>
                </section>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
function ProfileForm() {
  const { customer, refresh } = useStore();
  const [name, setName] = useState(customer?.full_name || "");
  return (
    <section className="panel">
      <h2>
        <UserRound size={21} />
        {t("account.profile")}
      </h2>
      <div className="inline-form">
        <Field label={t("auth.fullName")}>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            minLength={2}
            maxLength={150}
          />
        </Field>
        <AsyncButton
          action={async () => {
            await api.patch("/me", { full_name: name });
            await refresh();
            toast.success(t("action.saved"));
          }}
          disabled={name.trim().length < 2}
        >
          {t("account.editProfile")}
        </AsyncButton>
      </div>
    </section>
  );
}
function Verification() {
  const { customer, config, refresh } = useStore();
  const [uploading, setUploading] = useState("");
  const [error, setError] = useState("");
  if (!customer) return null;
  const messages = config?.settings.verification_messages as
    Record<string, string> | undefined;
  return (
    <>
      <div className="application-timeline" aria-label="Application progress">
        {[
          "Contact verified",
          "Business registered",
          "Certificates",
          "Team approval",
        ].map((item, i) => (
          <div
            key={item}
            className={
              i < 2 ||
              (i === 2 && !customer.missing_documents.length) ||
              customer.customer.status === "VERIFIED"
                ? "complete"
                : ""
            }
          >
            <span>{i + 1}</span>
            {item}
          </div>
        ))}
      </div>
      <section className="panel application-status">
        <div className="section-heading">
          <h2>{t("account.verification")}</h2>
          <Badge
            kind={
              customer.customer.status === "VERIFIED" ? "success" : "warning"
            }
          >
            {label(customer.customer.status)}
          </Badge>
        </div>
        <p>{messages?.[customer.customer.status]}</p>
        {customer.customer.status === "UNDER_REVIEW" && (
          <p className="muted">
            Your application is with our team. Your certificates are securely
            saved and locked for review. We’ll notify your verified contact when
            a decision is made.
          </p>
        )}
        {customer.customer.status === "VERIFIED" && (
          <Link className="btn" to="/catalog">
            Your store is ready <ArrowRight size={17} />
          </Link>
        )}
        <AsyncButton className="text-link" action={refresh}>
          Check latest status
        </AsyncButton>
        {customer.customer.rejection_reason && (
          <p className="error-box">{customer.customer.rejection_reason}</p>
        )}
      </section>
      <section className="panel">
        <h2>Your business certificates</h2>
        <p className="muted">{t("account.documentsBody")}</p>
        <div className="document-list">
          {["TIN", "TMDA", "PHARMACY_COUNCIL", "TBS"].map((type) => {
            const document = customer.documents.find(
              (d) => d.doc_type === type,
            );
            return (
              <div className="document-card" key={type}>
                <FileCheck2 size={24} strokeWidth={1.4} />
                <div>
                  <strong>{t(`account.doc.${type}`)}</strong>
                  <p>{document?.original_filename || t("account.missing")}</p>
                  {document?.notes && (
                    <p className="error-text">{document.notes}</p>
                  )}
                </div>
                {document && (
                  <>
                    <Badge
                      kind={
                        document.status === "APPROVED"
                          ? "success"
                          : document.status === "REJECTED"
                            ? "danger"
                            : "warning"
                      }
                    >
                      {document.status === "PENDING"
                        ? t("account.submitted")
                        : label(document.status)}
                    </Badge>
                    <AsyncButton
                      className="icon-button"
                      action={() =>
                        download(
                          `/documents/${document.id}/download`,
                          document.original_filename,
                        )
                      }
                    >
                      <Download size={17} />
                      <span className="sr-only">Download certificate</span>
                    </AsyncButton>
                  </>
                )}
                {["PENDING", "REJECTED"].includes(customer.customer.status) && (
                  <label className="upload-label btn secondary">
                    {uploading === type
                      ? t("action.loading")
                      : t("account.upload")}
                    <input
                      className="sr-only"
                      type="file"
                      accept="application/pdf,image/jpeg,image/png"
                      aria-label={`${t("account.upload")} ${t(`account.doc.${type}`)}`}
                      disabled={!!uploading}
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        if (!file) return;
                        if (file.size > 10 * 1024 * 1024) {
                          setError("Please choose a file smaller than 10 MB.");
                          e.target.value = "";
                          return;
                        }
                        setUploading(type);
                        setError("");
                        try {
                          const form = new FormData();
                          form.append("doc_type", type);
                          form.append("file", file);
                          await upload("/documents", form);
                          await refresh();
                        } catch (e) {
                          setError(
                            e instanceof Error
                              ? e.message
                              : t("error.unexpected"),
                          );
                        } finally {
                          setUploading("");
                          e.target.value = "";
                        }
                      }}
                    />
                  </label>
                )}
              </div>
            );
          })}
        </div>
        {error && (
          <p className="error-box" role="alert">
            {error}
          </p>
        )}
        {["PENDING", "REJECTED"].includes(customer.customer.status) && (
          <AsyncButton
            action={async () => {
              await api.post("/verification/submit");
              await refresh();
              toast.success(t("account.submitted"));
            }}
            disabled={!!customer.missing_documents.length}
          >
            {t("account.submitReview")}
            <ArrowRight size={17} />
          </AsyncButton>
        )}
      </section>
    </>
  );
}
function Addresses() {
  const [form, setForm] = useState(false);
  const [editing, setEditing] = useState<Address>();
  const query = useQuery({
    queryKey: ["addresses"],
    queryFn: () => api.get<Page<Address>>("/addresses"),
  });
  if (query.isLoading) return <Skeleton cards={2} />;
  if (query.isError && query.data === undefined)
    return <ErrorState error={query.error} retry={() => query.refetch()} />;
  return (
    <>
      <div className="section-heading">
        <h2>{t("account.addresses")}</h2>
        <button
          className="btn secondary"
          onClick={() => {
            setEditing(undefined);
            setForm(!form);
          }}
        >
          <Plus size={16} />
          {t("address.add")}
        </button>
      </div>
      {form && (
        <section className="panel">
          <AddressForm
            key={editing?.id || "new"}
            initial={editing}
            onSaved={() => setForm(false)}
          />
        </section>
      )}
      <div className="saved-addresses">
        {query.data?.items.map((address) => (
          <section className="panel" key={address.id}>
            <div className="section-heading">
              <MapPin size={23} />
              {address.is_default && (
                <Badge kind="success">{t("address.defaultBadge")}</Badge>
              )}
            </div>
            <h3>{address.label}</h3>
            <p>{address.address}</p>
            <p className="muted">{address.region}</p>
            <p>
              {address.contact_person} {address.phone}
            </p>
            <div className="address-actions">
              <button
                className="text-link"
                onClick={() => {
                  setEditing(address);
                  setForm(true);
                }}
              >
                {t("action.edit")}
              </button>
              <AsyncButton
                className="text-link danger-text"
                action={async () => {
                  await api.delete(`/addresses/${address.id}`);
                  await query.refetch();
                }}
              >
                {t("action.remove")}
              </AsyncButton>
            </div>
          </section>
        ))}
      </div>
      {!query.data?.items.length && !form && (
        <Empty title={t("address.empty")} body={t("address.emptyBody")} />
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
    <Skeleton cards={3} />
  ) : query.isError && query.data === undefined ? (
    <ErrorState error={query.error} retry={() => query.refetch()} />
  ) : query.data?.items.length ? (
    <div className="product-grid account-products">
      {query.data.items.map((p) => (
        <div key={p.id}>
          <ProductCard product={p} />
          <AsyncButton
            className="remove-favourite text-link"
            action={async () => {
              await api.delete(`/favourites/${p.id}`);
              await query.refetch();
            }}
          >
            <Trash2 size={14} />
            {t("action.remove")}
          </AsyncButton>
        </div>
      ))}
    </div>
  ) : (
    <Empty
      title={t("account.noFavourites")}
      body={t("account.noFavouritesBody")}
      action={
        <Link className="btn" to="/catalog">
          {t("action.browse")}
        </Link>
      }
    />
  );
}
type Template = {
  id: string;
  name: string;
  items: { product_id: string; quantity: number; name: string }[];
};
function Templates() {
  const { refresh } = useStore();
  const query = useQuery({
    queryKey: ["templates"],
    queryFn: () => api.get<Page<Template>>("/templates"),
  });
  return query.isLoading ? (
    <Skeleton cards={2} />
  ) : query.isError && query.data === undefined ? (
    <ErrorState error={query.error} retry={() => query.refetch()} />
  ) : query.data?.items.length ? (
    <div className="template-list">
      {query.data.items.map((item) => (
        <section className="panel" key={item.id}>
          <div className="section-heading">
            <h2>{item.name}</h2>
            <Bookmark size={23} />
          </div>
          <ul>
            {item.items.map((i) => (
              <li key={i.product_id}>
                {i.quantity} × {i.name}
              </li>
            ))}
          </ul>
          <div className="order-actions">
            <AsyncButton
              action={async () => {
                await api.post(`/templates/${item.id}/add-to-cart`);
                await refresh();
                toast.success(t("action.added"));
              }}
            >
              {t("account.addTemplate")}
              <Plus size={17} />
            </AsyncButton>
            <AsyncButton
              className="btn secondary"
              action={async () => {
                await api.delete(`/templates/${item.id}`);
                await query.refetch();
              }}
            >
              {t("action.delete")}
            </AsyncButton>
          </div>
        </section>
      ))}
    </div>
  ) : (
    <Empty
      title={t("account.noTemplates")}
      body={t("account.noTemplatesBody")}
      action={
        <Link className="btn" to="/cart">
          {t("nav.cart")}
        </Link>
      }
    />
  );
}
function Notifications() {
  const query = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<Page<Content>>("/notifications"),
  });
  return query.isLoading ? (
    <Skeleton cards={2} />
  ) : query.isError && query.data === undefined ? (
    <ErrorState error={query.error} retry={() => query.refetch()} />
  ) : query.data?.items.length ? (
    <div className="notification-list">
      {query.data.items.map((item) => (
        <section
          className={`panel notification ${item.read_at ? "read" : ""}`}
          key={item.id}
        >
          <Bell size={22} />
          <div>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
            <small>{new Date(String(item.created_at)).toLocaleString()}</small>
          </div>
          {!item.read_at && (
            <AsyncButton
              className="icon-button"
              action={async () => {
                await api.post(`/notifications/${item.id}/read`);
                await query.refetch();
              }}
            >
              <Check size={18} />
              <span className="sr-only">{t("account.markRead")}</span>
            </AsyncButton>
          )}
          {typeof (item.payload as { order_id?: string })?.order_id ===
            "string" && (
            <Link
              to={`/account/orders/${(item.payload as { order_id: string }).order_id}`}
              className="icon-button"
              aria-label={t("order.detail")}
            >
              <ArrowRight size={18} />
            </Link>
          )}
        </section>
      ))}
    </div>
  ) : (
    <Empty
      title={t("account.noNotifications")}
      body={t("account.noNotificationsBody")}
      icon={<Bell size={32} strokeWidth={1.4} />}
    />
  );
}
function Security() {
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: () =>
      api.get<
        Page<{
          id: string;
          device_label: string;
          current: boolean;
          created_at: string;
        }>
      >("/auth/sessions"),
  });
  function clear() {
    tokenStore.set(null);
    queryClient.clear();
    navigate("/login");
  }
  async function change(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/auth/password/change", {
        current_password: oldPassword,
        password,
      });
      clear();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error.unexpected"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="panel">
        <h2>{t("account.changePassword")}</h2>
        <form className="form-stack" onSubmit={change}>
          <Field label={t("account.currentPassword")}>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
            />
          </Field>
          <Field label={t("auth.newPassword")} hint={t("auth.passwordHint")}>
            <input
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              maxLength={72}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          {error && (
            <p className="error-box" role="alert">
              {error}
            </p>
          )}
          <button className="btn" disabled={busy}>
            {t("account.changePassword")}
          </button>
        </form>
      </section>
      <section className="panel application-status">
        <div className="section-heading">
          <h2>{t("account.devices")}</h2>
          <AsyncButton
            className="text-link danger-text"
            action={async () => {
              await api.post("/auth/logout-all");
              clear();
            }}
          >
            {t("account.signOutAll")}
          </AsyncButton>
        </div>
        {sessions.isError && sessions.data === undefined ? (
          <ErrorState error={sessions.error} retry={() => sessions.refetch()} />
        ) : (
          sessions.data?.items.map((session) => (
            <div className="session-row" key={session.id}>
              <MonitorSmartphone size={23} />
              <div>
                <strong>{session.device_label}</strong>
                <small>{new Date(session.created_at).toLocaleString()}</small>
              </div>
              {session.current && (
                <Badge kind="success">{t("account.currentDevice")}</Badge>
              )}
              <AsyncButton
                className="text-link"
                action={async () => {
                  await api.delete(`/auth/sessions/${session.id}`);
                  if (session.current) clear();
                  else await sessions.refetch();
                }}
              >
                {t("account.revoke")}
              </AsyncButton>
            </div>
          ))
        )}
      </section>
    </>
  );
}
