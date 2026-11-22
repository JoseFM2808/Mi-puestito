import { create } from 'zustand'
import { SinConexion, pedir } from '../../api/cliente'
import {
  aCentimos,
  aSoles,
  type AmbitoGasto,
  type CategoriaGasto,
  type GastoCable,
  type GastosDelDiaCable,
  type MedioPago,
} from '../../api/contrato'
import { baseDe } from '../../sincronizacion/base-local'
import { encolar } from '../../sincronizacion/cola'

/**
 * Gastos del día, offline-first como Ventas (ADR-032): anotar o borrar cambia la pantalla al
 * instante, se guarda en el dispositivo y se encola para el servidor. Sin red se siguen
 * anotando; al volver la conexión la cola los entrega en orden y es idempotente por uuid.
 */

/** "2026-11-17": el día peruano, igual que el servidor (America/Lima) */
export function diaPeruano(momento = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(momento)
}

export interface NuevoGasto {
  centimos: number
  medio: MedioPago
  ambito: AmbitoGasto
  categoria: CategoriaGasto
  descripcion?: string
}

/** Cuánto salió por medio y por ámbito, en céntimos (para mostrar; el servidor tiene la verdad) */
export function totales(gastos: GastoCable[]) {
  const suma = (filtro: (g: GastoCable) => boolean) =>
    gastos.filter(filtro).reduce((total, g) => total + aCentimos(g.monto), 0)
  return {
    efectivo: suma((g) => g.medio === 'efectivo'),
    yape: suma((g) => g.medio === 'yape_plin'),
    puesto: suma((g) => g.ambito === 'puesto'),
    hogar: suma((g) => g.ambito === 'hogar'),
  }
}

interface EstadoGastos {
  proyecto: string | null
  dia: string
  gastos: GastoCable[]
  /** true cuando lo mostrado viene del dispositivo y no del servidor */
  desdeDispositivo: boolean
  iniciar: (proyecto: string) => Promise<void>
  cargar: () => Promise<void>
  anotar: (gasto: NuevoGasto) => Promise<void>
  anular: (uuid: string) => Promise<void>
}

export const useGastos = create<EstadoGastos>()((set, get) => ({
  proyecto: null,
  dia: diaPeruano(),
  gastos: [],
  desdeDispositivo: false,

  iniciar: async (proyecto) => {
    if (get().proyecto !== proyecto) set({ proyecto, gastos: [], dia: diaPeruano() })
    await get().cargar()
  },

  cargar: async () => {
    const { proyecto } = get()
    if (!proyecto) return
    const dia = diaPeruano()
    const base = baseDe(proyecto)
    try {
      const cable = await pedir<GastosDelDiaCable>('GET', `/api/gastos?dia=${dia}`)
      set({ dia, gastos: cable.gastos, desdeDispositivo: false })
      await base.transaction('rw', base.gastos, async () => {
        await base.gastos.where('dia').equals(dia).delete()
        await base.gastos.bulkPut(cable.gastos.map((g) => ({ ...g, dia })))
      })
    } catch (fallo) {
      if (!(fallo instanceof SinConexion)) throw fallo
      const guardados = await base.gastos.where('dia').equals(dia).sortBy('creado_en')
      // Se guardan con su día para buscarlos; en pantalla va el gasto tal como lo da el servidor
      const sinDia = guardados.map((guardado) => {
        const gasto: GastoCable & { dia?: string } = { ...guardado }
        delete gasto.dia
        return gasto
      })
      set({ dia, gastos: sinDia, desdeDispositivo: true })
    }
  },

  anotar: async ({ centimos, medio, ambito, categoria, descripcion }) => {
    const { proyecto } = get()
    if (!proyecto) throw new Error('Sin proyecto activo')
    const gasto: GastoCable = {
      uuid: crypto.randomUUID(),
      monto: aSoles(centimos),
      medio,
      ambito,
      categoria,
      descripcion: descripcion?.trim() || null,
      orden_compra_uuid: null,
      creado_en: new Date().toISOString(),
    }
    set({ gastos: [...get().gastos, gasto] })
    await baseDe(proyecto).gastos.put({ ...gasto, dia: diaPeruano() })
    await encolar(proyecto, {
      metodo: 'POST',
      ruta: '/api/gastos',
      descripcion: `Gasto de ${gasto.monto}`,
      cuerpo: {
        uuid: gasto.uuid,
        monto: gasto.monto,
        medio,
        ambito,
        categoria,
        descripcion: gasto.descripcion ?? undefined,
      },
    })
  },

  anular: async (uuid) => {
    const { proyecto, gastos } = get()
    if (!proyecto) throw new Error('Sin proyecto activo')
    const gasto = gastos.find((g) => g.uuid === uuid)
    set({ gastos: gastos.filter((g) => g.uuid !== uuid) })
    await baseDe(proyecto).gastos.delete(uuid)
    await encolar(proyecto, {
      metodo: 'DELETE',
      ruta: `/api/gastos/${uuid}`,
      descripcion: `Borrar gasto de ${gasto?.monto ?? ''}`.trim(),
    })
  },
}))
