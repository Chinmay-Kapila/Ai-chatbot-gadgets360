import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Separate, dedicated config for the embeddable-widget build — kept
// apart from the main app's vite.config.js (which still builds the
// normal dev/demo site in src/App.jsx unchanged) so neither build mode
// interferes with the other.
export default defineConfig({
  plugins: [react()],

  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },

  build: {
    outDir: 'dist-widget',
    emptyOutDir: true,
    lib: {
      entry: path.resolve(__dirname, 'src/widget-entry.jsx'),
      name: 'G360Chatbot',
      formats: ['iife'],
      fileName: () => 'chatbot.js',
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
})
