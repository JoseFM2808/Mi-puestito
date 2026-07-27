import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

/**
 * Preferencias del operador (Zustand).
 *
 * Tamaño de letra: tres niveles definidos en tokens.css. Cambiarlo escribe
 * `data-letra` en <html>, lo que re-escala TODA la interfaz (escala rem).
 * Se persiste en sessionStorage: dura la sesión del operador y vuelve a
 * "Normal" al abrir una sesión nueva (ver Design-System.md, sección 5).
 */

export type TamanoLetra = 'normal' | 'grande' | 'muygrande'

export const TAMANOS_LETRA: { valor: TamanoLetra; etiqueta: string }[] = [
  { valor: 'normal', etiqueta: 'Normal' },
  { valor: 'grande', etiqueta: 'Grande' },
  { valor: 'muygrande', etiqueta: 'Muy grande' },
]

interface EstadoPreferencias {
  tamanoLetra: TamanoLetra
  cambiarTamanoLetra: (tamano: TamanoLetra) => void
}

function aplicarTamanoLetra(tamano: TamanoLetra) {
  // tokens.css define html[data-letra="…"]; sin atributo aplica Normal (20px)
  if (tamano === 'normal') {
    delete document.documentElement.dataset.letra
  } else {
    document.documentElement.dataset.letra = tamano
  }
}

export const usePreferencias = create<EstadoPreferencias>()(
  persist(
    (set) => ({
      tamanoLetra: 'normal',
      cambiarTamanoLetra: (tamano) => {
        aplicarTamanoLetra(tamano)
        set({ tamanoLetra: tamano })
      },
    }),
    {
      name: 'preferencias-operador',
      storage: createJSONStorage(() => sessionStorage),
      onRehydrateStorage: () => (estado) => {
        // Al recargar dentro de la misma sesión, re-aplica el tamaño guardado
        if (estado) aplicarTamanoLetra(estado.tamanoLetra)
      },
    },
  ),
)
