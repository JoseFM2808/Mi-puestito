import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Fuente Lexend empaquetada localmente (offline-first: nada de CDNs)
import '@fontsource/lexend/400.css'
import '@fontsource/lexend/500.css'
import '@fontsource/lexend/600.css'
import '@fontsource/lexend/700.css'

// Fuente de verdad visual: se importa UNA sola vez desde docs/06-diseno
import '@tokens/tokens.css'
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
