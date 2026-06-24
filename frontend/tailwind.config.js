/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        base: {
          950: "#0B0F14",
          900: "#10161D",
          800: "#161D26",
          700: "#1F2832",
          600: "#2C3744",
          500: "#465160",
          400: "#6B7686",
          300: "#9AA3AF",
          200: "#C7CDD5",
          100: "#E7EAEE",
        },
        signal: {
          50: "#FFF1E8",
          100: "#FFDBC2",
          200: "#FFB683",
          300: "#FF8F4D",
          400: "#FF6A24",
          500: "#FF4800",
          600: "#D63C00",
          700: "#A82F00",
          800: "#7A2200",
          900: "#4C1500",
        },
        teal: {
          400: "#3FCBA8",
          500: "#1D9E75",
          600: "#0F6E56",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
