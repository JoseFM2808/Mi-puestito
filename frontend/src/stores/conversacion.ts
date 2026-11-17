import { create } from 'zustand'
import type { AccionSugeridaCable } from '../api/contrato'

/**
 * Conversación con el Asistente. Vive aquí y no dentro de la pantalla para que no se
 * pierda al ir a Ventas y volver, y para que el apartado y la ventana muestren la misma.
 * Solo en memoria: se borra al cerrar la app o al cambiar de negocio (no se guarda en
 * el dispositivo lo que se le preguntó).
 */

export interface MensajeAsistente {
  quienHabla: 'operador' | 'asistente'
  texto: string
  acciones?: AccionSugeridaCable[]
  idRespuesta?: string
  valorada?: boolean
  /** Lo que la app hizo sola con esta respuesta, dicho al operador: "Abrí Compras…" (ADR-047) */
  hecho?: string
  /** Esta respuesta dejó una orden llenada en Ventas, por guardar (ADR-049) */
  conBorrador?: boolean
}

export const SALUDO = 'Hola, soy tu Asistente. Pregúntame por tu caja de hoy o cómo hacer algo en la app.'

const inicial = (): MensajeAsistente[] => [{ quienHabla: 'asistente', texto: SALUDO }]

interface EstadoConversacion {
  proyecto: string | null
  mensajes: MensajeAsistente[]
  enviando: boolean
  /** Cada negocio tiene su propia conversación: nunca se mezclan */
  usarProyecto: (proyecto: string) => void
  agregar: (mensaje: MensajeAsistente) => void
  marcarValorada: (indice: number) => void
  setEnviando: (enviando: boolean) => void
  empezarDeNuevo: () => void
}

export const useConversacion = create<EstadoConversacion>()((set, get) => ({
  proyecto: null,
  mensajes: inicial(),
  enviando: false,
  usarProyecto: (proyecto) => {
    if (get().proyecto !== proyecto) set({ proyecto, mensajes: inicial(), enviando: false })
  },
  agregar: (mensaje) => set((estado) => ({ mensajes: [...estado.mensajes, mensaje] })),
  marcarValorada: (indice) =>
    set((estado) => ({
      mensajes: estado.mensajes.map((m, i) => (i === indice ? { ...m, valorada: true } : m)),
    })),
  setEnviando: (enviando) => set({ enviando }),
  empezarDeNuevo: () => set({ mensajes: inicial(), enviando: false }),
}))
