/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        tier: {
          essential: "#0ea5e9",
          standard: "#8b5cf6",
          premium: "#f59e0b",
        },
      },
    },
  },
  plugins: [],
};
