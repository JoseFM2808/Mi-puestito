import { create } from 'zustand'
import type { FormularioLlenadoCable, ItemBorradorCable } from '../api/contrato'

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

/** Pago de fiado, gasto o merma llenado (D-28): la pantalla de destino lo abre y lo quita */
export interface FormularioAsistente {
  proyecto: string
  formulario: FormularioLlenadoCable
  version: number
}

interface EstadoBorrador {
  borrador: BorradorAsistente | null
  formulario: FormularioAsistente | null
  ponerFormulario: (proyecto: string, formulario: FormularioLlenadoCable) => void
  /** La pantalla lo toma una vez: lo abre en su formulario de siempre y lo quita de aquí */
  tomarFormulario: (tipo: FormularioLlenadoCable['tipo'], proyecto: string) => FormularioLlenadoCable | null
  poner: (proyecto: string, items: ItemBorradorCable[], para?: string | null) => void
  descartar: () => void
}

export const useBorradorAsistente = create<EstadoBorrador>()((set, get) => ({
  borrador: null,
  formulario: null,
  ponerFormulario: (proyecto, formulario) =>
    set({ formulario: { proyecto, formulario, version: (get().formulario?.version ?? 0) + 1 } }),
  tomarFormulario: (tipo, proyecto) => {
    const actual = get().formulario
    if (!actual || actual.formulario.tipo !== tipo || actual.proyecto !== proyecto) return null
    set({ formulario: null })
    return actual.formulario
  },
  poner: (proyecto, items, para = null) =>
    set({ borrador: { proyecto, items, para, version: (get().borrador?.version ?? 0) + 1 } }),
  descartar: () => set({ borrador: null }),
}))
