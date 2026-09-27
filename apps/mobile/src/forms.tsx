import { useState } from "react";
import { Switch, View } from "react-native";
import type { Address } from "@kabisa/api-client";
import { api, queryClient } from "./api";
import { Action, Input, s, t, Txt } from "./ui";
export function AddressForm({
  initial,
  onSaved,
}: {
  initial?: Address;
  onSaved: (address: Address) => void;
}) {
  const [form, setForm] = useState({
    label: initial?.label || "",
    address: initial?.address || "",
    region: initial?.region || "",
    contact_person: initial?.contact_person || "",
    phone: initial?.phone || "",
    is_default: initial?.is_default || false,
  });
  return (
    <View style={s.gap}>
      {(["label", "address", "region", "contact_person", "phone"] as const).map(
        (key) => (
          <Input
            key={key}
            label={t(
              {
                label: "address.label",
                address: "address.address",
                region: "auth.region",
                contact_person: "address.contact",
                phone: "address.phone",
              }[key],
            )}
            value={form[key]}
            onChangeText={(value) => setForm({ ...form, [key]: value })}
            keyboardType={key === "phone" ? "phone-pad" : "default"}
            maxLength={key === "address" ? 2000 : 120}
          />
        ),
      )}
      <View style={s.between}>
        <Txt>{t("address.default")}</Txt>
        <Switch
          accessibilityLabel={t("address.default")}
          value={form.is_default}
          onValueChange={(is_default) => setForm({ ...form, is_default })}
        />
      </View>
      <Action
        label={t("action.save")}
        disabled={
          !form.label.trim() ||
          form.address.trim().length < 5 ||
          form.region.trim().length < 2
        }
        onPress={async () => {
          const value = initial
            ? await api.patch<Address>(`/addresses/${initial.id}`, form)
            : await api.post<Address>("/addresses", form);
          await queryClient.invalidateQueries({ queryKey: ["addresses"] });
          onSaved(value);
        }}
      />
    </View>
  );
}
