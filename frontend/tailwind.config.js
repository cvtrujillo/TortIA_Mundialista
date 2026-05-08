/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        pitch: {
          950: "#050f0a",
          900: "#0a1f14",
          800: "#102b1b",
          700: "#1a3d27",
        },
        gold: {
          400: "#f5c842",
          500: "#e6b800",
          600: "#b38f00",
        },
      },
      fontFamily: {
        display: ["'Bebas Neue'", "Impact", "sans-serif"],
        body: ["'DM Sans'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
    },
  },
  plugins: [],
};
