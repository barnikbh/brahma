/** Tokens from design-system-mapping.md (refined mockups). */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { 900: "#312E81", 700: "#4338CA", 200: "#C7D2FE", 50: "#EEF2FF" },
        "sage-page": "#F1F4F0",
        "sage-note": "#E6EEE4",
        "sage-line": "#BFCDBB",
        "sage-ink": "#2F4034",
        ink: { DEFAULT: "#171717", quiet: "#525252" },
        explore: "#A21CAF",
        result: { bad: "#B91C1C", ok: "#15803D", pending: "#B45309" },
      },
      fontFamily: {
        serif: ["Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      fontSize: { base: ["14px", "1.5"] },
      borderRadius: { card: "8px" },
    },
  },
  plugins: [],
};
