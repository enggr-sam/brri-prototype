/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Prefer a Bengali-capable font stack for the response area.
        bengali: [
          "Noto Sans Bengali",
          "SolaimanLipi",
          "system-ui",
          "sans-serif",
        ],
      },
      colors: {
        brri: {
          green: "#15803d",
          dark: "#14532d",
          light: "#dcfce7",
        },
      },
    },
  },
  plugins: [],
};
