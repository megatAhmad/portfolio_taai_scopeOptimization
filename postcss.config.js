/**
 * PostCSS Configuration
 * 
 * Updated for Tailwind CSS v4 which requires @tailwindcss/postcss
 * instead of using tailwindcss directly as a plugin.
 */

export default {
  plugins: {
    '@tailwindcss/postcss': {},
    autoprefixer: {},
  },
};
