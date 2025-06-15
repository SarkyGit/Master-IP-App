import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'js',
    emptyOutDir: false,
    rollupOptions: {
      input: './src/index.jsx',
      output: {
        entryFileNames: 'bundle.js',
        format: 'es',
      },
    },
  },
});
