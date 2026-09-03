/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAFAF7",
        ink: "#171B1F",
        "ink-muted": "#5B6168",
        "ink-faint": "#8A9098",
        rule: "#DEDAD2",
        "rule-strong": "#C7C2B6",
        accent: "#2B4C7E",
        "accent-soft": "#E8EDF4",
        recovered: "#2E7D5B",
        "recovered-soft": "#E7F1EC",
        unresolved: "#A23B2E",
        "unresolved-soft": "#F5E9E6",
        review: "#9C6B0B",
        "review-soft": "#F5EEDD",
        rejected: "#6B4A7E",
        "rejected-soft": "#EFE8F2",
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
