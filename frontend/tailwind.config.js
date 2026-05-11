/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          orange: "#F26A21",
          "orange-light": "#F97316",
          navy: "#0B1633",
          "navy-light": "#1E2D4A",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          muted: "#F8F7F5",
          card: "rgba(255,255,255,0.75)",
        },
        muted: {
          DEFAULT: "#6B7280",
          light: "#9CA3AF",
        },
        border: {
          DEFAULT: "#E5E7EB",
          light: "#F3F4F6",
        },
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
        "3xl": "2rem",
        full: "9999px",
      },
      boxShadow: {
        card: "0 8px 24px rgba(0,0,0,0.05)",
        "card-hover": "0 12px 32px rgba(0,0,0,0.08)",
        button: "0 8px 20px rgba(242,106,33,0.25)",
        nav: "0 1px 3px rgba(0,0,0,0.04)",
      },
    },
  },
  plugins: [],
};
