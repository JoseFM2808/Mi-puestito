import { create } from 'zustand'

/**
 * Pantalla visible. Sin librería de rutas: son pocas pantallas y el hash
 * (#ventas) basta para que recargar la página no saque al operador de donde
 * estaba. El AI Companion puede navegar llamando a `irA`.
 */

export type Pantalla = 'caja' | 'ventas' | 'fiados'

export const PANTALLAS: { clave: Pantalla; nombre: string }[] = [
  { clave: 'caja', nombre: 'Caja de hoy' },
  { clave: 'ventas', nombre: 'Ventas' },
  { clave: 'fiados', nombre: 'Fiados' },
]

function desdeHash(): Pantalla {
  const clave = window.location.hash.replace('#', '')
  return PANTALLAS.some((p) => p.clave === clave) ? (clave as Pantalla) : 'caja'
}

interface EstadoNavegacion {
  pantalla: Pantalla
  /** Al entrar a Ventas desde "Venta rápida" se abre directo ese formulario */
  abrirVentaRapida: boolean
  menuAbierto: boolean
  asistenteAbierto: boolean
  irA: (pantalla: Pantalla, opciones?: { ventaRapida?: boolean }) => void
  alternarMenu: () => void
  alternarAsistente: () => void
  ventaRapidaAtendida: () => void
}

export const useNavegacion = create<EstadoNavegacion>()((set) => ({
  pantalla: desdeHash(),
  abrirVentaRapida: false,
  menuAbierto: false,
  asistenteAbierto: false,
  irA: (pantalla, opciones) => {
    // pushState y no replaceState: el botón Atrás de la tablet debe volver a la pantalla anterior
    if (window.location.hash !== `#${pantalla}`) window.history.pushState(null, '', `#${pantalla}`)
    set({ pantalla, menuAbierto: false, abrirVentaRapida: Boolean(opciones?.ventaRapida) })
  },
  alternarMenu: () => set((estado) => ({ menuAbierto: !estado.menuAbierto, asistenteAbierto: false })),
  alternarAsistente: () =>
    set((estado) => ({ asistenteAbierto: !estado.asistenteAbierto, menuAbierto: false })),
  ventaRapidaAtendida: () => set({ abrirVentaRapida: false }),
}))

// Atrás/Adelante del navegador, o un enlace a #ventas: la pantalla sigue al hash
window.addEventListener('hashchange', () => {
  const pantalla = desdeHash()
  if (useNavegacion.getState().pantalla !== pantalla) useNavegacion.setState({ pantalla, menuAbierto: false })
})
