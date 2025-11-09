import type { Config } from "tailwindcss";

export default {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        // Palette primaire accessible
        primary: {
          50: "var(--primary-50)",
          100: "var(--primary-100)",
          200: "var(--primary-200)",
          300: "var(--primary-300)",
          400: "var(--primary-400)",
          500: "var(--primary-500)",
          600: "var(--primary-600)",
          700: "var(--primary-700)",
          800: "var(--primary-800)",
          900: "var(--primary-900)",
        },
        // Couleurs sémantiques
        success: {
          light: "var(--success-light)",
          DEFAULT: "var(--success)",
          dark: "var(--success-dark)",
        },
        warning: {
          light: "var(--warning-light)",
          DEFAULT: "var(--warning)",
          dark: "var(--warning-dark)",
        },
        error: {
          light: "var(--error-light)",
          DEFAULT: "var(--error)",
          dark: "var(--error-dark)",
        },
        info: {
          light: "var(--info-light)",
          DEFAULT: "var(--info)",
          dark: "var(--info-dark)",
        },
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(-10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-down": {
          "0%": { height: "0", opacity: "0" },
          "100%": { height: "var(--radix-accordion-content-height)", opacity: "1" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.3s ease-out",
        "slide-down": "slide-down 0.2s ease-out",
      },
    },
  },
  plugins: [],
} satisfies Config;
