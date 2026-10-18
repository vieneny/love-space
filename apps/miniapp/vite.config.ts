import { defineConfig, loadEnv } from 'vite'
import uniModule from '@dcloudio/vite-plugin-uni'

const uni = (uniModule as unknown as { default?: typeof uniModule }).default || uniModule
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const base = env.VITE_API_BASE_URL || env.VITE_API_BASE || ''
  if (mode === 'production' && base && !base.startsWith('https://')) {
    throw new Error('Production VITE_API_BASE_URL must use HTTPS. Use dev:h5 for a local HTTP API.')
  }
  return { plugins: [uni()], server: { host: '127.0.0.1', port: 15174, strictPort: true } }
})
