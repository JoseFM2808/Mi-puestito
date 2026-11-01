import { create } from 'zustand'

/** ¿Hay una versión nueva de la app lista para aplicarse? (D-18, ver pwa.ts) */
interface EstadoActualizacion {
  hayVersionNueva: boolean
  aplicar: () => void
}

export const useActualizacion = create<EstadoActualizacion>()(() => ({
  hayVersionNueva: false,
  aplicar: () => {},
}))
