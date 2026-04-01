/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#102a43',
        ocean: '#1d4ed8',
        mist: '#eef6ff',
        sand: '#fff7ed',
        ember: '#c2410c',
        pine: '#166534',
      },
      fontFamily: {
        display: ['Space Grotesk', 'ui-sans-serif', 'system-ui'],
        body: ['Manrope', 'ui-sans-serif', 'system-ui'],
      },
      boxShadow: {
        panel: '0 24px 60px -32px rgba(16, 42, 67, 0.35)',
      },
      backgroundImage: {
        grid: 'linear-gradient(rgba(16,42,67,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(16,42,67,0.06) 1px, transparent 1px)',
      },
    },
  },
  plugins: [],
}
