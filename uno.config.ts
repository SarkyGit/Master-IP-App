import { defineConfig, presetUno } from 'unocss'

/**
 * UnoCSS configuration defining shortcuts for the Dark Colourful theme.
 * These shortcuts provide semantic class names for the various button
 * variants and table utilities used across the templates. A safelist is
 * also included so UnoCSS generates the classes even when they appear
 * dynamically (e.g. via Jinja templates).
 */

export default defineConfig({
  presets: [
    presetUno(),
  ],
  extract: {
    include: ['web-client/templates/**/*.html'],
  },
  // Semantic shortcuts used throughout the templates
  shortcuts: {
    'table-cell': 'px-4 py-2 border-b border-gray-700',
    'table-header': 'bg-gray-800 text-white',
  },
  // Ensure UnoCSS includes the shortcuts even when used dynamically
  safelist: [
    'table-cell', 'table-header', 'w-[0.375rem]', 'h-[0.375rem]',
  ],
})
