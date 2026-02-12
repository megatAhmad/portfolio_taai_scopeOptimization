# Frontend Setup Instructions

## Tailwind CSS PostCSS Configuration Fix

This project has been configured to use **Tailwind CSS v4** with the new `@tailwindcss/postcss` plugin architecture.

### Error Fixed

The error you encountered:
```
[plugin:vite:css] [postcss] It looks like you're trying to use `tailwindcss` directly as a PostCSS plugin...
```

Has been resolved by:
1. Creating [`postcss.config.js`](postcss.config.js) with `@tailwindcss/postcss` plugin
2. Creating [`tailwind.config.js`](tailwind.config.js) for Tailwind configuration
3. Creating [`package.json`](package.json) with correct dependencies
4. Creating [`vite.config.js`](vite.config.js) for Vite build configuration

### Installation Steps

1. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

2. **Run the development server:**
   ```bash
   npm run dev
   ```

3. **Build for production:**
   ```bash
   npm run build
   ```

### Configuration Files Created

- **[`postcss.config.js`](postcss.config.js)** - PostCSS configuration using `@tailwindcss/postcss`
- **[`tailwind.config.js`](tailwind.config.js)** - Tailwind CSS configuration
- **[`vite.config.js`](vite.config.js)** - Vite build tool configuration
- **[`package.json`](package.json)** - Node.js dependencies and scripts

### Key Changes from Tailwind CSS v3 to v4

**Old Configuration (v3):**
```javascript
// postcss.config.js
module.exports = {
  plugins: {
    tailwindcss: {},  // ❌ No longer works in v4
    autoprefixer: {},
  }
}
```

**New Configuration (v4):**
```javascript
// postcss.config.js
export default {
  plugins: {
    '@tailwindcss/postcss': {},  // ✅ Correct for v4
    autoprefixer: {},
  },
};
```

### Dependencies Installed

- `@tailwindcss/postcss@^4.0.0` - New PostCSS plugin for Tailwind CSS v4
- `tailwindcss@^4.0.0` - Tailwind CSS framework
- `postcss@^8.4.49` - PostCSS processor
- `autoprefixer@^10.4.20` - Autoprefixer plugin
- `vite@^6.0.0` - Vite build tool

### Troubleshooting

If you still encounter issues:

1. **Clear node_modules and reinstall:**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **Clear Vite cache:**
   ```bash
   rm -rf node_modules/.vite
   npm run dev
   ```

3. **Verify Node.js version:**
   ```bash
   node --version  # Should be v18 or higher
   ```

### Alternative: Downgrade to Tailwind CSS v3

If you prefer to use Tailwind CSS v3 instead:

```bash
npm install -D tailwindcss@^3 postcss@^8 autoprefixer@^10
```

Then update [`postcss.config.js`](postcss.config.js):
```javascript
export default {
  plugins: {
    tailwindcss: {},  // v3 syntax
    autoprefixer: {},
  },
};
```
