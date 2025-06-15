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
  // Semantic shortcuts used throughout the templates
  shortcuts: {
    'btn':
      'rounded px-3 py-1 text-sm font-medium shadow-sm transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-green': 'bg-green-600 text-white hover:bg-green-700',
    'btn-yellow': 'bg-yellow-500 text-black hover:bg-yellow-600',
    'btn-blue': 'bg-sky-500 text-white hover:bg-sky-600',
    'btn-red': 'bg-red-600 text-white hover:bg-red-700',
    'btn-grey': 'bg-gray-600 text-white hover:bg-gray-700',
    'btn-purple': 'bg-purple-500 text-white hover:bg-purple-600',
    'btn-orange': 'bg-orange-500 text-white hover:bg-orange-600',
    'btn-cyan': 'bg-cyan-500 text-white hover:bg-cyan-600',
    'table-cell': 'px-4 py-2 border-b border-gray-700',
    'table-header': 'bg-gray-800 text-white',
  },
  // Ensure UnoCSS includes the shortcuts even when used dynamically
  safelist: [
    'btn',
    'btn-green', 'btn-yellow', 'btn-blue', 'btn-red', 'btn-grey',
    'btn-purple', 'btn-orange', 'btn-cyan',
    'table-cell', 'table-header',
  ],
})
