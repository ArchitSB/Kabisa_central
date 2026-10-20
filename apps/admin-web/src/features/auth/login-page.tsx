import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import axios from "axios";
import {
  ArrowRight,
  PackageCheck,
  ClipboardList,
  Store,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/features/auth/auth-store";
import type { ApiErrorResponse } from "@/features/auth/types";

const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid admin email."),
  password: z.string().min(8, "Password must contain at least 8 characters."),
});

type LoginValues = z.infer<typeof loginSchema>;
type ReturnLocation = {
  pathname: string;
  search?: string;
};

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const prefersReducedMotion = useReducedMotion();
  const login = useAuthStore((state) => state.login);
  const bootstrap = useAuthStore((state) => state.bootstrap);
  const status = useAuthStore((state) => state.status);
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  useEffect(() => {
    if (status === "checking") {
      void bootstrap();
    }
  }, [bootstrap, status]);

  useEffect(() => {
    if (status === "anonymous") {
      setFocus("email");
    }
  }, [setFocus, status]);

  if (status === "authenticated") {
    return <Navigate to="/" replace />;
  }

  if (status === "checking") {
    return (
      <main
        className="flex min-h-screen items-center justify-center bg-background px-6"
        role="status"
        aria-live="polite"
      >
        <div className="text-center">
          <LoaderCircle
            aria-hidden="true"
            className="mx-auto size-6 animate-spin text-primary-700"
          />
          <p className="mt-3 text-sm font-medium text-secondary">
            Checking your secure session…
          </p>
        </div>
      </main>
    );
  }

  async function onSubmit(values: LoginValues) {
    setServerError(null);
    try {
      await login(values.email, values.password);
      const from = (location.state as { from?: ReturnLocation } | null)?.from;
      const queryReturnTo = new URLSearchParams(location.search).get("returnTo");
      const safeQueryReturnTo =
        queryReturnTo?.startsWith("/") && !queryReturnTo.startsWith("//")
          ? queryReturnTo
          : null;
      const destination = from
        ? `${from.pathname}${from.search ?? ""}`
        : (safeQueryReturnTo ?? "/");
      navigate(destination, { replace: true });
    } catch (error) {
      const detail = axios.isAxiosError<ApiErrorResponse>(error)
        ? error.response?.data.detail
        : null;
      setServerError(
        detail ?? "Sign-in could not be completed. Check your connection and try again.",
      );
      setFocus("email");
    }
  }

  return (
    <main className="ops-login">
      <section className="ops-login-story">
        <div className="ops-login-brand">
          <img
            src="/images/kabisa-logo.png"
            alt="Kabisa — One step for millions"
            width="176"
            height="80"
          />
          <span>OPERATIONS</span>
        </div>
        <div className="ops-login-narrative">
          <p className="ops-login-eyebrow">BEHIND EVERY BETTER DAY</p>
          <h1>
            Good care starts
            <br />
            with a team
            <br />
            <em>in sync.</em>
          </h1>
          <p>
            One connected place for the people, products and decisions that keep Kabisa
            moving.
          </p>
          <div className="ops-login-flow" aria-hidden="true">
            <span>
              <Store size={20} />
              Customers
            </span>
            <i />
            <span>
              <ClipboardList size={20} />
              Orders
            </span>
            <i />
            <span>
              <PackageCheck size={20} />
              Delivery
            </span>
          </div>
        </div>
        <div className="ops-login-footnote">
          <span>One step for millions.</span>
          <span>Dar es Salaam · Tanzania</span>
        </div>
      </section>

      <section className="ops-login-form-side">
        <motion.div
          initial={prefersReducedMotion ? false : { y: 12, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{
            duration: prefersReducedMotion ? 0 : 0.22,
            ease: [0.2, 0, 0, 1],
          }}
          className="min-w-0 w-full max-w-[460px]"
        >
          <img
            className="ops-login-mobile-logo"
            src="/images/kabisa-logo.png"
            alt="Kabisa"
            width="160"
            height="73"
          />
          <div className="ops-login-form">
            <div className="flex size-11 items-center justify-center rounded-[12px] bg-primary-100 text-primary-800">
              <ShieldCheck aria-hidden="true" className="size-5" />
            </div>
            <p className="mt-6 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
              WELCOME TO YOUR WORKSPACE
            </p>
            <h2 className="mt-2 font-display text-[32px] font-semibold leading-tight tracking-[-0.025em] text-foreground">
              Welcome back.
            </h2>
            <p className="mt-2 text-sm leading-6 text-secondary">
              Sign in to manage your Kabisa operations.
            </p>

            <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
              <div>
                <label
                  htmlFor="email"
                  className="mb-2 block text-sm font-semibold text-foreground"
                >
                  Email address
                </label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  inputMode="email"
                  placeholder="name@company.com"
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={errors.email ? "email-error" : undefined}
                  {...register("email")}
                />
                {errors.email ? (
                  <p id="email-error" className="mt-1.5 text-xs font-medium text-danger">
                    {errors.email.message}
                  </p>
                ) : null}
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label
                    htmlFor="password"
                    className="text-sm font-semibold text-foreground"
                  >
                    Password
                  </label>
                  <span className="text-xs text-muted">Staff access</span>
                </div>
                <div className="relative">
                  <LockKeyhole
                    aria-hidden="true"
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
                  />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    className="px-10"
                    aria-invalid={Boolean(errors.password)}
                    aria-describedby={errors.password ? "password-error" : undefined}
                    {...register("password")}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    aria-pressed={showPassword}
                    className="absolute right-1 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-muted transition-colors duration-micro hover:bg-primary-50 hover:text-primary-800"
                  >
                    {showPassword ? (
                      <EyeOff aria-hidden="true" className="size-4" />
                    ) : (
                      <Eye aria-hidden="true" className="size-4" />
                    )}
                  </button>
                </div>
                {errors.password ? (
                  <p id="password-error" className="mt-1.5 text-xs font-medium text-danger">
                    {errors.password.message}
                  </p>
                ) : null}
              </div>

              {serverError ? (
                <div
                  role="alert"
                  className="rounded-control border border-danger/20 bg-danger-surface px-4 py-3 text-sm leading-5 text-danger"
                >
                  {serverError}
                </div>
              ) : null}

              <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <LoaderCircle aria-hidden="true" className="animate-spin" />
                    Signing in…
                  </>
                ) : (
                  <>
                    Enter workspace
                    <ArrowRight aria-hidden="true" />
                  </>
                )}
              </Button>
            </form>
          </div>

          <p className="mt-5 text-center text-xs leading-5 text-muted">
            Access is logged and limited by your assigned role.
          </p>
        </motion.div>
      </section>
    </main>
  );
}
