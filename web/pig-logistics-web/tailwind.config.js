/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {
        colors: {
          'brand-dark': '#0a192f',
          'brand-teal': '#64ffda',
          'brand-gray': '#8892b0',
        }
      },
    },
    plugins: [],
  }