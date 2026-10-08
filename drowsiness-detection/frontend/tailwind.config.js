/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["var(--font-sans)", "system-ui", "sans-serif"] },
      colors: {
        navy: { 950: "#060b16", 900: "#0a1222", 800: "#101b33", 700: "#18264a", 600: "#243763" },
        ink: "#e8eefb",
        mute: "#8fa1c4",
        ok: "#3fe0a0",
        warn: "#ffb54a",
        danger: "#ff5a73",
        accent: "#5b8cff",
      },
    },
  },
  plugins: [],
};
