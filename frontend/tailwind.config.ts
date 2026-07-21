import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0c1219",
          raised: "#121a24",
          border: "#1e2a3a",
        },
        accent: {
          DEFAULT: "#3d9cf0",
          muted: "#2a6fad",
        },
        long: "#22c55e",
        short: "#ef4444",
        warn: "#eab308",
      },
      fontFamily: {
        display: ["var(--font-display)", "Segoe UI", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
