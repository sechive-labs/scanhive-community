import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
  // `test` is read by Vitest, not Vite -- the top-level `vite` package here
  // and the `vite` vitest bundles internally are different (major) versions
  // with incompatible Plugin types, so importing defineConfig from
  // 'vitest/config' to type-check this field fails tsc -b. Cast past it
  // instead; Vite itself ignores the unknown `test` key at runtime.
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any)
