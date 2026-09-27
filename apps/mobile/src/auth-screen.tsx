import { useState } from "react";
import { Platform, Pressable, View } from "react-native";
import { router } from "expo-router";
import type { Tokens } from "@kabisa/api-client";
import { normalizePhone, passwordSchema } from "@kabisa/core";
import { api } from "./api";
import { useStore } from "./store";
import { Action, Input, Panel, Screen, s, t, Txt } from "./ui";
export function AuthScreen({ mode }: { mode: "login" | "register" | "reset" }) {
  const register = mode === "register",
    reset = mode === "reset";
  const { login, config } = useStore();
  const [step, setStep] = useState(0);
  const [otp, setOtp] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [challenge, setChallenge] = useState("");
  const [proof, setProof] = useState("");
  const [code, setCode] = useState("");
  const [delivery, setDelivery] = useState("");
  const [details, setDetails] = useState({
    full_name: "",
    business_name: "",
    business_type: "COMMUNITY_PHARMACY",
    phone: "",
    email: "",
    physical_address: "",
    region: "",
  });
  const otpFlow = otp || register || reset;
  async function done(session: Tokens) {
    await login(session);
    router.replace(register ? "/account/verification" : "/account");
  }
  async function submit() {
    if (!otpFlow) {
      await done(
        await api.post<Tokens>("/auth/login", {
          identifier,
          password,
          device_label: `Kabisa ${Platform.OS}`,
        }),
      );
      return;
    }
    if (step === 0) {
      const result = await api.post<{ challenge_id: string; delivery: string }>(
        "/auth/otp/request",
        {
          identifier,
          purpose: register
            ? "REGISTRATION"
            : reset
              ? "PASSWORD_RESET"
              : "LOGIN",
        },
      );
      setChallenge(result.challenge_id);
      setDelivery(result.delivery);
      setStep(1);
    } else if (step === 1) {
      const result = await api.post<{ verification_token: string }>(
        "/auth/otp/verify",
        { challenge_id: challenge, code },
      );
      setProof(result.verification_token);
      if (otp && !register && !reset) {
        await done(
          await api.post<Tokens>("/auth/login/otp", {
            verification_token: result.verification_token,
            device_label: `Kabisa ${Platform.OS}`,
          }),
        );
        return;
      }
      setDetails((old) => ({
        ...old,
        ...(identifier.includes("@")
          ? { email: identifier }
          : { phone: normalizePhone(identifier) }),
      }));
      setStep(2);
    } else {
      passwordSchema.parse(password);
      if (reset) {
        await api.post("/auth/password/reset", {
          verification_token: proof,
          password,
        });
        router.replace("/login");
      } else
        await done(
          await api.post<Tokens>("/auth/register", {
            ...details,
            phone: normalizePhone(details.phone),
            email: details.email || null,
            password,
            verification_token: proof,
          }),
        );
    }
  }
  return (
    <Screen
      title={t(
        register
          ? "auth.registerTitle"
          : reset
            ? "auth.resetTitle"
            : "auth.welcome",
      )}
      eyebrow="Kabisa Pharmacy"
      body={t(
        register
          ? "auth.registerBody"
          : reset
            ? "auth.resetBody"
            : "auth.loginBody",
      )}
    >
      <Panel>
        {(!otpFlow || step === 0) && (
          <Input
            label={t("auth.identifier")}
            value={identifier}
            onChangeText={setIdentifier}
            autoCapitalize="none"
            autoComplete="username"
            keyboardType="email-address"
          />
        )}
        {otpFlow && step === 1 && (
          <>
            <Txt>
              {t(delivery === "console" ? "auth.consoleCode" : "auth.codeSent")}
            </Txt>
            <Input
              label={t("auth.code")}
              value={code}
              onChangeText={(v) => setCode(v.replace(/\D/g, "").slice(0, 6))}
              keyboardType="number-pad"
              autoComplete="one-time-code"
              maxLength={6}
            />
            <Action
              secondary
              label={t("auth.resend")}
              onPress={() => {
                setStep(0);
                setCode("");
              }}
            />
          </>
        )}
        {register && step === 2 && (
          <>
            {(
              [
                "full_name",
                "business_name",
                "phone",
                "email",
                "physical_address",
                "region",
              ] as const
            ).map((key) => (
              <Input
                key={key}
                label={t(
                  {
                    full_name: "auth.fullName",
                    business_name: "auth.businessName",
                    phone: "auth.phone",
                    email: "auth.email",
                    physical_address: "auth.physicalAddress",
                    region: "auth.region",
                  }[key],
                )}
                value={details[key]}
                onChangeText={(v) => setDetails({ ...details, [key]: v })}
                autoCapitalize={key === "email" ? "none" : "sentences"}
                keyboardType={
                  key === "phone"
                    ? "phone-pad"
                    : key === "email"
                      ? "email-address"
                      : "default"
                }
              />
            ))}
            <Txt>{t("auth.businessType")}</Txt>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
              {[
                "COMMUNITY_PHARMACY",
                "DLDM",
                "WHOLESALE",
                "HOSPITAL",
                "CLINIC",
                "GOVERNMENT",
                "NGO",
                "FBO",
              ].map((type) => (
                <Pressable
                  key={type}
                  style={[
                    s.chip,
                    details.business_type === type && s.chipActive,
                  ]}
                  onPress={() =>
                    setDetails({ ...details, business_type: type })
                  }
                >
                  <Txt>{t(`business.${type}`)}</Txt>
                </Pressable>
              ))}
            </View>
          </>
        )}
        {(!otpFlow || step === 2) && (
          <Input
            label={t(reset ? "auth.newPassword" : "auth.password")}
            secureTextEntry
            value={password}
            onChangeText={setPassword}
            autoComplete={
              register || reset ? "new-password" : "current-password"
            }
            maxLength={72}
          />
        )}
        <Action
          label={t(
            !otpFlow
              ? "nav.login"
              : step === 0
                ? "action.send"
                : step === 1
                  ? "auth.verify"
                  : reset
                    ? "auth.reset"
                    : "auth.create",
          )}
          onPress={submit}
          disabled={
            (register && config?.settings.enable_registration === false) ||
            (step === 0 && !identifier.trim()) ||
            (step === 1 && code.length !== 6)
          }
        />
        {!register && !reset && (
          <>
            <Action
              secondary
              label={t(otp ? "auth.passwordLogin" : "auth.otpLogin")}
              onPress={() => {
                setOtp(!otp);
                setStep(0);
              }}
            />
            <Action
              secondary
              label={t("auth.forgot")}
              onPress={() => router.push("/forgot-password")}
            />
          </>
        )}
      </Panel>
      <Action
        secondary
        label={t(register ? "nav.login" : "nav.register")}
        onPress={() => router.replace(register ? "/login" : "/register")}
      />
      <Action
        secondary
        label={t("page.backHome")}
        onPress={() => router.replace("/")}
      />
    </Screen>
  );
}
