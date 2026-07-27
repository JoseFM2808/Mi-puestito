import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig } from 'vitest/config'

// tokens.css vive en docs/06-diseno (fuente de verdad visual, ver Design-System.md).
// Se importa directo desde ahí: no se copia para evitar que las versiones se desvíen.
const rutaDiseno = fileURLToPath(new URL('../docs/06-diseno', import.meta.url))

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icono.svg', 'apple-touch-icon.png'],
      workbox: {
        // En la app de escritorio el API comparte origen con la interfaz:
        // sin esta lista, el service worker respondería /api y /docs con la
        // cáscara de la aplicación en vez de la respuesta real.
        navigateFallbackDenylist: [/^\/api/, /^\/docs/, /^\/openapi\.json/, /^\/redoc/],
      },
      manifest: {
        name: 'Mi Puestito',
        short_name: 'Mi Puestito',
        description: 'Gestión de ventas, compras y caja para pequeños vendedores',
        lang: 'es-PE',
        display: 'standalone',
        background_color: '#FAF7F2',
        theme_color: '#1E6E42',
        icons: [
          { src: 'pwa-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          // maskable: Android recorta el ícono a la forma del sistema
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
          { src: 'icono.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@tokens': rutaDiseno,
    },
  },
  server: {
    // Permite servir tokens.css desde docs/, fuera de la raíz del frontend
    fs: { allow: ['..'] },
  },
  test: {
    environment: 'jsdom',
  },
})
