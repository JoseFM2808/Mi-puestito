import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig, type Plugin } from 'vitest/config'

// tokens.css vive en docs/06-diseno (fuente de verdad visual, ver Design-System.md).
// Se importa directo desde ahí: no se copia para evitar que las versiones se desvíen.
const rutaDiseno = fileURLToPath(new URL('../docs/06-diseno', import.meta.url))

/**
 * El manifest de la PWA y la <meta theme-color> no pueden leer variables CSS:
 * necesitan el hex. En vez de copiarlo a mano (y que se desvíe), se lee de
 * tokens.css al construir. Si el token no existe, el build falla.
 */
function colorDeToken(nombre: string): string {
  const tokens = readFileSync(`${rutaDiseno}/tokens.css`, 'utf8')
  const coincidencia = tokens.match(new RegExp(`--${nombre}:\\s*(#[0-9A-Fa-f]{6})`))
  if (!coincidencia) throw new Error(`tokens.css no define --${nombre}`)
  return coincidencia[1]
}

const COLOR_FONDO = colorDeToken('fondo')
const COLOR_PRIMARIO = colorDeToken('primario')

/** Reemplaza %COLOR_PRIMARIO% en index.html por el token. */
function coloresEnHtml(): Plugin {
  return {
    name: 'colores-desde-tokens',
    transformIndexHtml: (html) => html.replaceAll('%COLOR_PRIMARIO%', COLOR_PRIMARIO),
  }
}

export default defineConfig({
  plugins: [
    react(),
    coloresEnHtml(),
    VitePWA({
      // 'prompt': la versión nueva se aplica cuando el operador lo decide (no en medio de una venta)
      registerType: 'prompt',
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
        background_color: COLOR_FONDO,
        theme_color: COLOR_PRIMARIO,
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
    // En desarrollo el backend corre aparte (puerto 8000); en la app de
    // escritorio empaquetada comparten origen. Este proxy hace que el
    // frontend siempre pueda llamar a fetch('/api/...') igual en los dos casos.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/pruebas/preparar.ts'],
  },
})
