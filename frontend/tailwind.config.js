/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        display: [
          "Inter",
          "Noto Sans Bengali",
          "system-ui",
          "sans-serif",
        ],
        bengali: [
          "Noto Sans Bengali",
          "Inter",
          "system-ui",
          "sans-serif",
        ],
        sans: [
          "Inter",
          "Noto Sans Bengali",
          "system-ui",
          "sans-serif",
        ],
      },
      colors: {
        brri: {
          green: "#2563eb",
          dark: "#0f172a",
          light: "#e2e8f0",
        },
        leaf: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#93c5fd",
          400: "#3b82f6",
          500: "#2563eb",
          600: "#1d4ed8",
          700: "#1e3a8a",
          800: "#1e293b",
          900: "#0f172a",
          950: "#0b1220",
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
