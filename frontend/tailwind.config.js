/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#030712',      // Near-black background
          surface: '#0B0F19', // Deep navy surface
          card: '#111827',    // Slightly lighter card surfaces
          border: '#1F2937',  // Restricted borders
          text: '#F9FAFB',
          textMuted: '#9CA3AF'
        }
      }
    },
  },
  plugins: [],
}
