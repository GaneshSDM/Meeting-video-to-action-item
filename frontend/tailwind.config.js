/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dm: {
          navy: '#0A192F',
          slate: '#112240',
          blue: '#0070f3',
          accent: '#64FFDA',
          text: '#CCD6F6',
          muted: '#8892B0'
        }
      }
    },
  },
  plugins: [],
}
