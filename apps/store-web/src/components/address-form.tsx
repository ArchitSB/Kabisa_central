import { useState, type FormEvent } from "react";
import type { Address } from "@kabisa/api-client";
import { toast } from "sonner";
import { api, queryClient } from "../lib/api";
import { t } from "../i18n";
import { Field } from "./ui";
export function AddressForm({
  onSaved,
  initial,
}: {
  onSaved: (value: Address) => void;
  initial?: Address;
}) {
  const [data, setData] = useState({
    label: initial?.label || "",
    address: initial?.address || "",
    region: initial?.region || "",
    contact_person: initial?.contact_person || "",
    phone: initial?.phone || "",
    is_default: initial?.is_default || false,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const value = await (initial
        ? api.patch<Address>(`/addresses/${initial.id}`, data)
        : api.post<Address>("/addresses", data));
      await queryClient.invalidateQueries({ queryKey: ["addresses"] });
      toast.success(t("action.saved"));
      onSaved(value);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error.unexpected"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="form-stack address-form" onSubmit={submit}>
      {(["label", "address", "region", "contact_person", "phone"] as const).map(
        (key) => (
          <Field
            key={key}
            label={t(
              key === "region"
                ? "auth.region"
                : key === "contact_person"
                  ? "address.contact"
                  : `address.${key}`,
            )}
          >
            <input
              required={["label", "address", "region"].includes(key)}
              minLength={key === "address" ? 5 : key === "region" ? 2 : 1}
              maxLength={key === "address" ? 2000 : 120}
              value={data[key]}
              onChange={(e) => setData({ ...data, [key]: e.target.value })}
              autoComplete={
                key === "address"
                  ? "street-address"
                  : key === "region"
                    ? "address-level1"
                    : key === "phone"
                      ? "tel"
                      : "off"
              }
            />
          </Field>
        ),
      )}
      <label className="check-label">
        <input
          type="checkbox"
          checked={data.is_default}
          onChange={(e) => setData({ ...data, is_default: e.target.checked })}
        />
        {t("address.default")}
      </label>
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
      <button className="btn" disabled={busy}>
        {busy ? t("action.loading") : t("action.save")}
      </button>
    </form>
  );
}
