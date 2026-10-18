import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: { port: 15173, strictPort: true },
  preview: { port: 14173, strictPort: true },
  build: { sourcemap: false },
})
