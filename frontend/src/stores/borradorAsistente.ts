import { create } from 'zustand'
import type { ItemBorradorCable } from '../api/contrato'

/**
 * La orden que el Asistente llenó y espera que el operador revise y guarde (ADR-049).
 *
 * Vive aquí, fuera de Ventas y del Asistente, para que ninguno dependa del otro: el
 * Asistente la deja y Ventas la muestra. Solo en memoria y por negocio: nada se guarda
 * hasta que el operador toca «Guardar orden», y nunca la ve otro negocio.
 */

export interface BorradorAsistente {
  proyecto: string
  items: ItemBorradorCable[]
  /** Para quién es: será el nombre de la orden */
  para: string | null
  /** Cambia en cada borrador nuevo: el formulario de Ventas se vuelve a llenar */
  version: number
}

interface EstadoBorrador {
  borrador: BorradorAsistente | null
  poner: (proyecto: string, items: ItemBorradorCable[], para?: string | null) => void
  descartar: () => void
}

export const useBorradorAsistente = create<EstadoBorrador>()((set, get) => ({
  borrador: null,
  poner: (proyecto, items, para = null) =>
    set({ borrador: { proyecto, items, para, version: (get().borrador?.version ?? 0) + 1 } }),
  descartar: () => set({ borrador: null }),
}))
