import { create } from 'zustand'
import { ErrorApi, SinConexion, pedir } from '../api/cliente'
import { baseDe, type Operacion } from './base-local'

/**
 * Cola de sincronización offline-first (ADR-032, docs/02-arquitectura/
 * Sincronizacion-Offline.md).
 *
 * Toda escritura de Ventas pasa por aquí: se guarda en IndexedDB ANTES de
 * enviarse, así una venta nunca se pierde por falta de red. Reglas:
 *
 * - FIFO, de a una: "agregar producto" nunca llega antes que "abrir orden".
 * - Sin red → se detiene y reintenta al volver la conexión.
 * - El servidor rechaza (4xx) → queda como "rechazada", con el motivo, para
 *   mostrársela al operador; la cola sigue con las demás.
 * - Error del servidor (5xx) → se detiene y reintenta más tarde.
 * - Reenviar es seguro: el servidor es idempotente por uuid.
 */

export type Enviar = (operacion: Operacion) => Promise<unknown>

type AlAplicar = (operacion: Operacion, respuesta: unknown) => void

interface EstadoSincronizacion {
  pendientes: number
  rechazadas: Operacion[]
  sincronizando: boolean
  sinConexion: boolean
}

export const useSincronizacion = create<EstadoSincronizacion>()(() => ({
  pendientes: 0,
  rechazadas: [],
  sincronizando: false,
  sinConexion: false,
}))

const escuchas = new Set<AlAplicar>()

/** Recibe cada operación que el servidor aceptó, con su respuesta. */
export function alAplicarOperacion(escucha: AlAplicar): () => void {
  escuchas.add(escucha)
  return () => escuchas.delete(escucha)
}

const enviarPorDefecto: Enviar = (operacion) => pedir(operacion.metodo, operacion.ruta, operacion.cuerpo)

let procesando: Promise<void> | null = null

async function actualizarConteos(proyecto: string): Promise<void> {
  const base = baseDe(proyecto)
  useSincronizacion.setState({
    pendientes: await base.operaciones.where('estado').equals('pendiente').count(),
    rechazadas: await base.operaciones.where('estado').equals('rechazada').toArray(),
  })
}

/** Guarda la operación en el dispositivo y dispara su envío. */
export async function encolar(
  proyecto: string,
  operacion: Pick<Operacion, 'metodo' | 'ruta' | 'descripcion'> & { cuerpo?: Record<string, unknown> },
  enviar: Enviar = enviarPorDefecto,
): Promise<void> {
  const creadaEn = new Date().toISOString()
  await baseDe(proyecto).operaciones.add({
    ...operacion,
    // La hora real de la venta viaja con ella (el usuario nunca la escribe)
    cuerpo: operacion.cuerpo ? { ocurrido_en: creadaEn, ...operacion.cuerpo } : undefined,
    creadaEn,
    estado: 'pendiente',
    intentos: 0,
  })
  await actualizarConteos(proyecto)
  void procesarCola(proyecto, enviar)
}

/** Envía las pendientes en orden. Una sola ejecución a la vez. */
export function procesarCola(proyecto: string, enviar: Enviar = enviarPorDefecto): Promise<void> {
  if (procesando) return procesando
  procesando = (async () => {
    const base = baseDe(proyecto)
    useSincronizacion.setState({ sincronizando: true })
    try {
      for (;;) {
        const siguiente = await base.operaciones.where('estado').equals('pendiente').first()
        if (!siguiente?.id) break
        try {
          const respuesta = await enviar(siguiente)
          await base.operaciones.delete(siguiente.id)
          useSincronizacion.setState({ sinConexion: false })
          for (const escucha of escuchas) escucha(siguiente, respuesta)
        } catch (error) {
          if (error instanceof ErrorApi && error.esDefinitivo) {
            await base.operaciones.update(siguiente.id, { estado: 'rechazada', error: error.detalle })
            continue
          }
          await base.operaciones.update(siguiente.id, { intentos: siguiente.intentos + 1 })
          useSincronizacion.setState({ sinConexion: error instanceof SinConexion })
          break // sin red o servidor caído: se reintenta después
        } finally {
          await actualizarConteos(proyecto)
        }
      }
    } finally {
      useSincronizacion.setState({ sincronizando: false })
      procesando = null
    }
  })()
  return procesando
}

/** El operador leyó el rechazo y lo descarta. */
export async function descartarRechazada(proyecto: string, id: number): Promise<void> {
  await baseDe(proyecto).operaciones.delete(id)
  await actualizarConteos(proyecto)
}

/**
 * Reintenta al recuperar la red y cada cierto tiempo. Devuelve la función
 * para detenerlo (al cerrar sesión).
 */
export function iniciarSincronizacion(proyecto: string, intervaloMs = 20_000): () => void {
  const intentar = () => void procesarCola(proyecto)
  void actualizarConteos(proyecto).then(intentar)
  window.addEventListener('online', intentar)
  const temporizador = window.setInterval(intentar, intervaloMs)
  return () => {
    window.removeEventListener('online', intentar)
    window.clearInterval(temporizador)
  }
}

/** Espera a que la cola termine su vuelta actual (tests y cierres ordenados). */
export async function esperarCola(): Promise<void> {
  while (procesando) await procesando
}
