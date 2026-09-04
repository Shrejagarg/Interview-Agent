import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        heading: ["var(--font-heading)", "sans-serif"],
      },
      colors: {
        background: "#080808", // Almost black
        foreground: "#FAFAFA",
        brutal: {
          dark: "#111111",
          border: "rgba(255,255,255,0.15)",
        },
        accent: {
          DEFAULT: "#F4A4B4", // Soft pink
          hover: "#FFC1CC",
        },
      },
      letterSpacing: {
        tighter: "-0.04em",
        tightest: "-0.06em",
      },
    },
  },
  plugins: [],
};
export default config;
