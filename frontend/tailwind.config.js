/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: [
          "Sora",
          "Noto Sans Bengali",
          "system-ui",
          "sans-serif",
        ],
        bengali: [
          "Noto Sans Bengali",
          "SolaimanLipi",
          "system-ui",
          "sans-serif",
        ],
        sans: [
          "Sora",
          "Noto Sans Bengali",
          "system-ui",
          "sans-serif",
        ],
      },
      colors: {
        brri: {
          green: "#1a7a45",
          dark: "#0f3d2e",
          light: "#d8efe0",
        },
        leaf: {
          50: "#f3faf5",
          100: "#e4f3ea",
          200: "#c5e4d0",
          300: "#95cfaa",
          400: "#5fb37e",
          500: "#1a7a45",
          800: "#1a4d36",
          900: "#143d2c",
          950: "#0f3d2e",
        },
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "soft-pulse": {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.7s ease-out both",
        "soft-pulse": "soft-pulse 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
