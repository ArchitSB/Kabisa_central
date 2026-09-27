import tokens from "./tokens.json" with { type: "json" };
export default {
  theme: {
    extend: {
      colors: tokens.colors,
      fontFamily: {
        display: [tokens.fonts.display, "Georgia", "serif"],
        sans: [tokens.fonts.body, "sans-serif"],
      },
      borderRadius: Object.fromEntries(
        Object.entries(tokens.radii).map(([key, value]) => [key, `${value}px`]),
      ),
      transitionDuration: { standard: `${tokens.motion.standard}ms` },
      transitionTimingFunction: {
        kabisa: `cubic-bezier(${tokens.motion.easing.join(",")})`,
      },
    },
  },
};
