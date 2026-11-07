import { create } from 'zustand'

/**
 * Pantalla visible. Sin librería de rutas: son pocas pantallas y el hash
 * (#ventas) basta para que recargar la página no saque al operador de donde
 * estaba. El AI Companion puede navegar llamando a `irA`.
 */

export type Pantalla = 'caja' | 'ventas' | 'fiados' | 'compras' | 'inventario' | 'asistente'

/**
 * El menú lateral muestra cada pantalla con su nombre y, debajo, para qué sirve:
 * quien usa la app por primera vez no tiene que adivinar qué hay detrás de cada botón.
 */
export const PANTALLAS: { clave: Pantalla; nombre: string; ayuda: string }[] = [
  { clave: 'caja', nombre: 'Caja de hoy', ayuda: 'Cuánto vendiste hoy' },
  { clave: 'ventas', nombre: 'Ventas', ayuda: 'Registrar y cobrar' },
  { clave: 'fiados', nombre: 'Fiados', ayuda: 'Quién te debe' },
  { clave: 'compras', nombre: 'Compras', ayuda: 'Pedidos a proveedores' },
  { clave: 'inventario', nombre: 'Inventario', ayuda: 'Cuánto te queda' },
  { clave: 'asistente', nombre: 'Asistente', ayuda: 'Pregúntale lo que necesites' },
]

function desdeHash(): Pantalla {
  const clave = window.location.hash.replace('#', '')
  return PANTALLAS.some((p) => p.clave === clave) ? (clave as Pantalla) : 'caja'
}

interface EstadoNavegacion {
  pantalla: Pantalla
  /** La última pantalla que no fue el Asistente: a ella se vuelve al pasarlo a ventana */
  anterior: Pantalla
  /** Al entrar a Ventas desde "Venta rápida" se abre directo ese formulario */
  abrirVentaRapida: boolean
  /** Solo en pantalla angosta: el menú lateral se abre sobre el contenido */
  menuAbierto: boolean
  /**
   * El Asistente en ventana flotante, sobre la pantalla actual. Sigue abierta al cambiar
   * de pantalla: el operador ve la app mientras el Asistente lo guía o actúa en ella.
   */
  asistenteFlotante: boolean
  irA: (pantalla: Pantalla, opciones?: { ventaRapida?: boolean }) => void
  alternarMenu: () => void
  cerrarMenu: () => void
  alternarAsistenteFlotante: () => void
  cerrarAsistenteFlotante: () => void
  /** Del apartado a la ventana: vuelve a la pantalla de trabajo con el Asistente encima */
  asistenteAVentana: () => void
  ventaRapidaAtendida: () => void
}

export const useNavegacion = create<EstadoNavegacion>()((set, get) => ({
  pantalla: desdeHash(),
  anterior: desdeHash() === 'asistente' ? 'caja' : desdeHash(),
  abrirVentaRapida: false,
  menuAbierto: false,
  asistenteFlotante: false,
  irA: (pantalla, opciones) => {
    // pushState y no replaceState: el botón Atrás de la tablet debe volver a la pantalla anterior
    if (window.location.hash !== `#${pantalla}`) window.history.pushState(null, '', `#${pantalla}`)
    set({
      pantalla,
      anterior: pantalla === 'asistente' ? get().anterior : pantalla,
      menuAbierto: false,
      abrirVentaRapida: Boolean(opciones?.ventaRapida),
      // En el apartado del Asistente la ventana sobra: es la misma conversación
      asistenteFlotante: pantalla === 'asistente' ? false : get().asistenteFlotante,
    })
    // Pantalla nueva, empieza arriba: nadie debe buscar dónde quedó el contenido
    window.scrollTo?.({ top: 0 })
  },
  alternarMenu: () => set((estado) => ({ menuAbierto: !estado.menuAbierto })),
  cerrarMenu: () => set({ menuAbierto: false }),
  alternarAsistenteFlotante: () => set((estado) => ({ asistenteFlotante: !estado.asistenteFlotante })),
  cerrarAsistenteFlotante: () => set({ asistenteFlotante: false }),
  asistenteAVentana: () => {
    get().irA(get().anterior)
    set({ asistenteFlotante: true })
  },
  ventaRapidaAtendida: () => set({ abrirVentaRapida: false }),
}))

// Atrás/Adelante del navegador, o un enlace a #ventas: la pantalla sigue al hash
window.addEventListener('hashchange', () => {
  const pantalla = desdeHash()
  const estado = useNavegacion.getState()
  if (estado.pantalla !== pantalla) {
    useNavegacion.setState({
      pantalla,
      menuAbierto: false,
      anterior: pantalla === 'asistente' ? estado.anterior : pantalla,
      asistenteFlotante: pantalla === 'asistente' ? false : estado.asistenteFlotante,
    })
  }
})
