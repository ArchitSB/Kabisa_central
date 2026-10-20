import { useState, type FormEvent } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { ArrowRight, Check, Eye, EyeOff, ShieldCheck } from "lucide-react";
import type { Customer, Tokens } from "@kabisa/api-client";
import { normalizePhone } from "@kabisa/core";
import { api } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { t } from "../i18n";
import { Field } from "../components/ui";
export default function Auth() {
  const location = useLocation();
  const isRegister = location.pathname === "/register";
  const isReset = location.pathname === "/forgot-password";
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { login, config } = useStore();
  const [step, setStep] = useState(0);
  const [otpMode, setOtpMode] = useState(false);
  const [challenge, setChallenge] = useState("");
  const [proof, setProof] = useState("");
  const [code, setCode] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
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
  const title = isRegister
    ? t("auth.registerTitle")
    : isReset
      ? t("auth.resetTitle")
      : t("auth.welcome");
  useSeo(title);
  const otpFlow = isRegister || isReset || otpMode;
  const returnTo = params.get("returnTo");
  async function done(tokens: Tokens) {
    await login(tokens);
    const profile = await api.get<Customer>("/me");
    navigate(
      isRegister || profile.customer.status !== "VERIFIED"
        ? "/account/verification"
        : returnTo?.startsWith("/") && !returnTo.startsWith("//")
          ? returnTo
          : "/",
      { replace: true },
    );
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (!otpFlow) {
        await done(
          await api.post<Tokens>("/auth/login", {
            identifier,
            password,
            device_label: "Kabisa web",
          }),
        );
      } else if (step === 0) {
        const result = await api.post<{
          challenge_id: string;
          delivery: string;
        }>("/auth/otp/request", {
          identifier,
          purpose: isRegister
            ? "REGISTRATION"
            : isReset
              ? "PASSWORD_RESET"
              : "LOGIN",
        });
        setChallenge(result.challenge_id);
        setDelivery(result.delivery);
        setStep(1);
      } else if (step === 1) {
        const result = await api.post<{ verification_token: string }>(
          "/auth/otp/verify",
          { challenge_id: challenge, code },
        );
        setProof(result.verification_token);
        if (otpMode && !isRegister && !isReset)
          await done(
            await api.post<Tokens>("/auth/login/otp", {
              verification_token: result.verification_token,
              device_label: "Kabisa web",
            }),
          );
        else {
          setDetails((previous) => ({
            ...previous,
            ...(identifier.includes("@")
              ? { email: identifier }
              : { phone: normalizePhone(identifier) }),
          }));
          setStep(2);
        }
      } else if (isReset) {
        await api.post("/auth/password/reset", {
          verification_token: proof,
          password,
        });
        navigate("/login", { state: { message: t("auth.resetDone") } });
      } else {
        await done(
          await api.post<Tokens>("/auth/register", {
            ...details,
            email: details.email || null,
            phone: normalizePhone(details.phone),
            password,
            verification_token: proof,
          }),
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error.unexpected"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="container auth-page" key={location.pathname}>
      <aside className="auth-story">
        <img
          src="/images/pharmacy-partner.webp"
          alt="Illustrative Tanzanian pharmacist portrait"
        />
        <div className="auth-story-copy">
          <p className="eyebrow">ONE STEP FOR MILLIONS</p>
          <h2>
            A better day
            <br />
            begins together.
          </h2>
          <p>
            Your business. Your supplies.
            <br />A partner who understands both.
          </p>
          <span>
            <ShieldCheck size={18} /> A verified healthcare business community
          </span>
        </div>
      </aside>
      <section className="auth-form-section">
        <p className="eyebrow">
          {isRegister
            ? t("nav.register")
            : isReset
              ? t("auth.forgot")
              : t("nav.login")}
        </p>
        <h1>{title}</h1>
        <p className="muted">
          {isRegister
            ? t("auth.registerBody")
            : isReset
              ? t("auth.resetBody")
              : t("auth.loginBody")}
        </p>
        {isRegister && (
          <p className="application-note">
            Complete your business details and upload your certificates. Our
            team will approve your account before you can browse or order.
          </p>
        )}
        {isRegister && (
          <div className="onboarding-progress">
            {["auth.contactStep", "auth.detailsStep", "auth.documentsStep"].map(
              (key, i) => (
                <div
                  key={key}
                  className={i <= (step === 2 ? 1 : 0) ? "active" : ""}
                >
                  <span>
                    {i === 0 && step === 2 ? <Check size={13} /> : i + 1}
                  </span>
                  {t(key)}
                </div>
              ),
            )}
          </div>
        )}
        {location.state?.message && (
          <p className="inline-notice">{location.state.message}</p>
        )}
        {isRegister && config?.settings.enable_registration === false ? (
          <p className="error-box">{t("error.maintenance")}</p>
        ) : (
          <form className="form-stack" onSubmit={submit}>
            {(!otpFlow || step === 0) && (
              <Field label={t("auth.identifier")}>
                <input
                  type="text"
                  inputMode="email"
                  autoComplete="username"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  required
                  maxLength={320}
                  placeholder="you@business.co.tz or +255…"
                />
              </Field>
            )}
            {otpFlow && step === 1 && (
              <>
                <p className="inline-notice">
                  {delivery === "console"
                    ? t("auth.consoleCode")
                    : t("auth.codeSent")}
                </p>
                <Field label={t("auth.code")}>
                  <input
                    className="otp-input"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={code}
                    onChange={(e) =>
                      setCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                    }
                    pattern="[0-9]{6}"
                    required
                    maxLength={6}
                  />
                </Field>
                <button
                  type="button"
                  className="text-link"
                  onClick={() => {
                    setStep(0);
                    setCode("");
                  }}
                >
                  {t("auth.resend")}
                </button>
              </>
            )}
            {isRegister && step === 2 && (
              <>
                <Field label={t("auth.fullName")}>
                  <input
                    value={details.full_name}
                    required
                    minLength={2}
                    autoComplete="name"
                    onChange={(e) =>
                      setDetails({ ...details, full_name: e.target.value })
                    }
                  />
                </Field>
                <Field label={t("auth.businessName")}>
                  <input
                    value={details.business_name}
                    required
                    minLength={2}
                    autoComplete="organization"
                    onChange={(e) =>
                      setDetails({ ...details, business_name: e.target.value })
                    }
                  />
                </Field>
                <Field label={t("auth.businessType")}>
                  <select
                    value={details.business_type}
                    onChange={(e) =>
                      setDetails({ ...details, business_type: e.target.value })
                    }
                  >
                    {["COMMUNITY_PHARMACY", "DLDM", "WHOLESALE"].map((type) => (
                      <option value={type} key={type}>
                        {t(`business.${type}`)}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="form-columns">
                  <Field label={t("auth.phone")}>
                    <input
                      type="tel"
                      required
                      value={details.phone}
                      onChange={(e) =>
                        setDetails({ ...details, phone: e.target.value })
                      }
                      autoComplete="tel"
                    />
                  </Field>
                  <Field label={t("auth.email")}>
                    <input
                      type="email"
                      value={details.email}
                      onChange={(e) =>
                        setDetails({ ...details, email: e.target.value })
                      }
                      autoComplete="email"
                    />
                  </Field>
                </div>
                <Field label={t("auth.physicalAddress")}>
                  <input
                    required
                    minLength={5}
                    value={details.physical_address}
                    onChange={(e) =>
                      setDetails({
                        ...details,
                        physical_address: e.target.value,
                      })
                    }
                    autoComplete="street-address"
                  />
                </Field>
                <Field label={t("auth.region")}>
                  <input
                    required
                    minLength={2}
                    value={details.region}
                    onChange={(e) =>
                      setDetails({ ...details, region: e.target.value })
                    }
                    autoComplete="address-level1"
                  />
                </Field>
              </>
            )}
            {(!otpFlow || step === 2) && (
              <Field
                label={isReset ? t("auth.newPassword") : t("auth.password")}
                hint={
                  isRegister || isReset ? t("auth.passwordHint") : undefined
                }
              >
                <div className="password-field">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    minLength={8}
                    maxLength={72}
                    autoComplete={
                      isRegister || isReset
                        ? "new-password"
                        : "current-password"
                    }
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </Field>
            )}
            {!otpFlow && (
              <Link className="text-link" to="/forgot-password">
                {t("auth.forgot")}
              </Link>
            )}
            {error && (
              <p className="error-box" role="alert">
                {error}
              </p>
            )}
            <button className="btn full" disabled={busy}>
              {busy
                ? t("action.loading")
                : !otpFlow
                  ? t("nav.login")
                  : step === 0
                    ? t("action.send")
                    : step === 1
                      ? t("auth.verify")
                      : isReset
                        ? t("auth.reset")
                        : t("auth.create")}
              <ArrowRight size={17} />
            </button>
          </form>
        )}
        {!isRegister && !isReset && (
          <button
            className="auth-alternate text-link"
            onClick={() => {
              setOtpMode(!otpMode);
              setStep(0);
              setError("");
            }}
          >
            {otpMode ? t("auth.passwordLogin") : t("auth.otpLogin")}
          </button>
        )}
        <p className="auth-switch">
          {isRegister ? t("auth.haveAccount") : t("auth.noAccount")}{" "}
          <Link to={isRegister ? "/login" : "/register"}>
            {isRegister ? t("nav.login") : t("nav.register")}
          </Link>
        </p>
      </section>
    </div>
  );
}
