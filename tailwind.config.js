/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#1e2826',
        mint: '#c9f276',
        teal: '#117e79',
        paper: '#f5f7f4',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        card: '0 18px 50px rgba(21, 44, 39, 0.08)',
      },
    },
  },
  plugins: [],
}
