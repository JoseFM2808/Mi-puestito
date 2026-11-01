import Dexie, { type Table } from 'dexie'
import type {
  ClienteCable,
  OrdenCompraCable,
  ProveedorCable,
  ResumenDashboardCable,
  VentaCable,
} from '../api/contrato'
import type { MetodoHttp } from '../api/cliente'

/**
 * Base local del dispositivo (IndexedDB vía Dexie, AGENTS.md).
 *
 * Una base POR PROYECTO, igual que en el servidor: lo practicado en demo
 * nunca se mezcla con el negocio real, ni siquiera en la tablet.
 */

export interface Operacion {
  id?: number
  /** Hora del dispositivo al hacerla (el servidor la respeta si es razonable) */
  creadaEn: string
  metodo: Exclude<MetodoHttp, 'GET'>
  ruta: string
  cuerpo?: Record<string, unknown>
  /** Qué fue, en palabras del operador: "Cobrar Orden 2" */
  descripcion: string
  estado: 'pendiente' | 'rechazada'
  intentos: number
  /** Motivo del rechazo, tal como lo dijo el servidor */
  error?: string
}

export class BaseLocal extends Dexie {
  operaciones!: Table<Operacion, number>
  ventasAbiertas!: Table<VentaCable, string>
  clientes!: Table<ClienteCable, string>
  instantaneas!: Table<{ clave: string; resumen: ResumenDashboardCable; guardadaEn: string }, string>
  ordenesCompra!: Table<OrdenCompraCable, string>
  proveedores!: Table<ProveedorCable, string>

  constructor(proyecto: string) {
    super(`mi-puestito-${proyecto}`)
    this.version(1).stores({
      operaciones: '++id, estado',
      ventasAbiertas: 'uuid',
      clientes: 'uuid, nombre',
      instantaneas: 'clave',
    })
    this.version(2).stores({
      ordenesCompra: 'uuid, estado',
      proveedores: 'uuid, nombre',
    })
  }
}

const bases = new Map<string, BaseLocal>()

export function baseDe(proyecto: string): BaseLocal {
  let base = bases.get(proyecto)
  if (!base) {
    base = new BaseLocal(proyecto)
    bases.set(proyecto, base)
  }
  return base
}

/** Solo para tests: olvida las conexiones abiertas. */
export function cerrarBases(): void {
  for (const base of bases.values()) base.close()
  bases.clear()
}
