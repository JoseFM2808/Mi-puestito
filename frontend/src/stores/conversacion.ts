import { create } from 'zustand'
import type { AccionSugeridaCable } from '../api/contrato'
import { baseDe } from '../sincronizacion/base-local'

/**
 * Conversación con el Asistente. Vive aquí y no dentro de la pantalla para que no se
 * pierda al ir a Ventas y volver, y para que el apartado y la ventana muestren la misma.
 *
 * Se guarda en el dispositivo, en la base local del negocio (D-26, ADR-052): recargar o
 * actualizar la app a mitad de una tarea ya no borra el hilo. Cada negocio tiene la suya y
 * nunca se mezclan. Se guardan los últimos `MAX_GUARDADOS` mensajes; «Empezar una
 * conversación nueva» la borra también del dispositivo.
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
  /** Lo que el Asistente guardó en su memoria con esta respuesta (D-26) */
  recordado?: string[]
}

export const SALUDO = 'Hola, soy tu Asistente. Pregúntame por tu caja de hoy o cómo hacer algo en la app.'
export const MAX_GUARDADOS = 40
const CLAVE = 'actual'

const inicial = (): MensajeAsistente[] => [{ quienHabla: 'asistente', texto: SALUDO }]

/** Guarda sin bloquear: si el dispositivo no deja (modo privado, sin espacio), solo no se recuerda */
function guardar(proyecto: string | null, mensajes: MensajeAsistente[]): Promise<void> {
  if (!proyecto) return Promise.resolve()
  const base = baseDe(proyecto)
  const ultimos =
    mensajes.length > MAX_GUARDADOS ? [mensajes[0], ...mensajes.slice(-(MAX_GUARDADOS - 1))] : mensajes
  const tarea =
    ultimos.length <= 1
      ? base.conversaciones.delete(CLAVE)
      : base.conversaciones.put({ clave: CLAVE, mensajes: ultimos, guardadaEn: new Date().toISOString() })
  return tarea.then(
    () => undefined,
    () => undefined,
  )
}

interface EstadoConversacion {
  proyecto: string | null
  mensajes: MensajeAsistente[]
  enviando: boolean
  /** Cada negocio tiene su propia conversación: nunca se mezclan. Trae la guardada. */
  usarProyecto: (proyecto: string) => Promise<void>
  agregar: (mensaje: MensajeAsistente) => void
  marcarValorada: (indice: number) => void
  setEnviando: (enviando: boolean) => void
  empezarDeNuevo: () => void
}

export const useConversacion = create<EstadoConversacion>()((set, get) => ({
  proyecto: null,
  mensajes: inicial(),
  enviando: false,
  usarProyecto: async (proyecto) => {
    if (get().proyecto === proyecto) return
    set({ proyecto, mensajes: inicial(), enviando: false })
    let guardada: MensajeAsistente[] | undefined
    try {
      guardada = (await baseDe(proyecto).conversaciones.get(CLAVE))?.mensajes
    } catch {
      return // sin almacenamiento local se empieza de cero, como antes
    }
    // Solo si sigue en el mismo negocio y aún no empezó a escribir otra cosa
    const ahora = get()
    if (guardada && guardada.length > 1 && ahora.proyecto === proyecto && ahora.mensajes.length === 1) {
      set({ mensajes: guardada })
    }
  },
  agregar: (mensaje) => {
    set((estado) => ({ mensajes: [...estado.mensajes, mensaje] }))
    void guardar(get().proyecto, get().mensajes)
  },
  marcarValorada: (indice) => {
    set((estado) => ({
      mensajes: estado.mensajes.map((m, i) => (i === indice ? { ...m, valorada: true } : m)),
    }))
    void guardar(get().proyecto, get().mensajes)
  },
  setEnviando: (enviando) => set({ enviando }),
  empezarDeNuevo: () => {
    set({ mensajes: inicial(), enviando: false })
    void guardar(get().proyecto, get().mensajes)
  },
}))

/** Solo para tests: espera a que lo último se haya guardado. */
export const guardarAhora = () =>
  guardar(useConversacion.getState().proyecto, useConversacion.getState().mensajes)
