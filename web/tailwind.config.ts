import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#fdf4ef",
          100: "#fae6d6",
          200: "#f4caaa",
          300: "#eca876",
          400: "#e38249",
          500: "#D97757",
          600: "#c9622e",
          700: "#a74b24",
          800: "#863c22",
          900: "#6c321f",
        },
        purple: {
          400: "#9b7fd4",
          500: "#7B5EA7",
          600: "#634d8a",
          700: "#4e3c6e",
        },
        surface: {
          900: "#1E1E2E",
          800: "#252535",
          700: "#2D2D3E",
          600: "#363650",
          500: "#4A4A6A",
          400: "#5e5e80",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 20px rgba(217, 119, 87, 0.15)",
        "glow-lg": "0 0 40px rgba(217, 119, 87, 0.2)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-up": "slideUp 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
