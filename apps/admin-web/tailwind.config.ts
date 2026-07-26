import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "rgb(var(--primary-50-rgb) / <alpha-value>)",
          100: "rgb(var(--primary-100-rgb) / <alpha-value>)",
          200: "rgb(var(--primary-200-rgb) / <alpha-value>)",
          300: "rgb(var(--primary-300-rgb) / <alpha-value>)",
          400: "rgb(var(--primary-400-rgb) / <alpha-value>)",
          500: "rgb(var(--primary-500-rgb) / <alpha-value>)",
          600: "rgb(var(--primary-600-rgb) / <alpha-value>)",
          700: "rgb(var(--primary-700-rgb) / <alpha-value>)",
          800: "rgb(var(--primary-800-rgb) / <alpha-value>)",
          900: "rgb(var(--primary-900-rgb) / <alpha-value>)",
          DEFAULT: "rgb(var(--primary-700-rgb) / <alpha-value>)",
          foreground: "#FFFFFF",
        },
        sidebar: {
          DEFAULT: "rgb(var(--sidebar-bg-rgb) / <alpha-value>)",
          foreground: "rgb(var(--sidebar-fg-rgb) / <alpha-value>)",
          muted: "rgb(var(--sidebar-fg-muted-rgb) / <alpha-value>)",
          active: "rgb(var(--sidebar-active-bg-rgb) / <alpha-value>)",
          accent: "rgb(var(--sidebar-accent-rgb) / <alpha-value>)",
        },
        background: "var(--bg)",
        surface: "rgb(var(--surface-rgb) / <alpha-value>)",
        border: "var(--border)",
        foreground: "var(--text)",
        secondary: "var(--text-secondary)",
        muted: "var(--text-muted)",
        success: {
          DEFAULT: "var(--success-fg)",
          surface: "var(--success-bg)",
        },
        warning: {
          DEFAULT: "var(--warning-fg)",
          surface: "var(--warning-bg)",
        },
        danger: {
          DEFAULT: "var(--danger-fg)",
          surface: "var(--danger-bg)",
        },
        neutral: {
          DEFAULT: "var(--neutral-fg)",
          surface: "var(--neutral-bg)",
        },
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "14px",
        control: "10px",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        drawer: "var(--shadow-drawer)",
      },
      transitionDuration: {
        micro: "120ms",
        standard: "220ms",
        spatial: "320ms",
      },
      transitionTimingFunction: {
        kabisa: "var(--ease-kabisa)",
      },
      keyframes: {
        "drawer-in": {
          from: { transform: "translateX(100%)" },
          to: { transform: "translateX(0)" },
        },
        "drawer-out": {
          from: { transform: "translateX(0)" },
          to: { transform: "translateX(100%)" },
        },
        "overlay-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "overlay-out": {
          from: { opacity: "1" },
          to: { opacity: "0" },
        },
      },
      animation: {
        "drawer-in": "drawer-in 320ms var(--ease-kabisa)",
        "drawer-out": "drawer-out 180ms ease-in",
        "overlay-in": "overlay-in 180ms ease-out",
        "overlay-out": "overlay-out 120ms ease-in",
      },
    },
  },
  plugins: [],
};

export default config;
