import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Fuente Lexend empaquetada localmente (offline-first: nada de CDNs)
import '@fontsource/lexend/400.css'
import '@fontsource/lexend/500.css'
import '@fontsource/lexend/600.css'
import '@fontsource/lexend/700.css'

// Fuente de verdad visual, UNA sola vez y en este orden (ADR-050): los tokens del estándar,
// generados desde tokens.json (colores, fuente, radios), y luego lo propio de la interfaz
import '@tokens/tokens/tokens.css'
import '@tokens/producto/tokens-producto.css'
import './estilos-base.css'

import { App } from './App'
import { registrarActualizaciones } from './pwa'

const raiz = document.getElementById('raiz')
if (!raiz) throw new Error('index.html no tiene el elemento #raiz')

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

registrarActualizaciones()
