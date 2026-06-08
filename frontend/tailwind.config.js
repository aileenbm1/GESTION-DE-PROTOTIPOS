/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#080B12',
        panel: '#0F1624',
        line: '#243047',
        accent: '#22C55E',
        signal: '#60A5FA',
      },
      boxShadow: {
        soft: '0 18px 60px rgba(0, 0, 0, .28)',
      },
    },
  },
  plugins: [],
};
