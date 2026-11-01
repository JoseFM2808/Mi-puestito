import { create } from 'zustand'
import { SinConexion, pedir } from '../../api/cliente'
import {
  aCentimos,
  aSoles,
  type EstadoRecepcion,
  type OrdenCompraCable,
  type ProveedorCable,
  type ResultadoOrdenCable,
} from '../../api/contrato'
import { baseDe } from '../../sincronizacion/base-local'
import { alAplicarOperacion, encolar, useSincronizacion } from '../../sincronizacion/cola'

/**
 * Estado del módulo Compras, offline-first como Ventas (ADR-032): cada acción cambia
 * la pantalla al instante, se guarda en el dispositivo y se encola. Al sincronizar, la
 * respuesta del servidor (la verdad: totales, avisos) reemplaza a la versión local.
 */

export interface EntradaRecepcion {
  itemUuid: string
  estado: EstadoRecepcion
  productoSustituto?: string
  montoSustitutoCentimos?: number
  /** Cuánto entra al stock, si el producto se lleva en Inventario */
  cantidadStock?: string
}

export interface ItemNuevo {
  nombre: string
  cantidad?: string
  centimos: number
}

/** Solo para mostrar al instante; el cálculo que manda es el del servidor (servicio.py). */
export function aplicarRecepcion(orden: OrdenCompraCable, entradas: EntradaRecepcion[]): OrdenCompraCable {
  const items = orden.items.map((item) => {
    const entrada = entradas.find((e) => e.itemUuid === item.uuid)
    if (!entrada || entrada.estado === 'pendiente') return item
    return {
      ...item,
      estado_recepcion: entrada.estado,
      producto_sustituto: entrada.productoSustituto ?? null,
      monto_sustituto:
        entrada.montoSustitutoCentimos === undefined ? null : aSoles(entrada.montoSustitutoCentimos),
    }
  })
  const real = items.reduce((total, item) => {
    if (item.estado_recepcion === 'recibido') return total + aCentimos(item.monto)
    if (item.estado_recepcion === 'cambiado') return total + aCentimos(item.monto_sustituto ?? '0')
    return total
  }, 0)
  return {
    ...orden,
    items,
    monto_real: aSoles(real),
    estado: items.every((item) => item.estado_recepcion !== 'pendiente') ? 'recibida' : orden.estado,
  }
}

/** Días de calendario peruano, sin depender de la zona del dispositivo: "2026-11-02". */
export function diaPeruano(diasDesdeHoy = 0): string {
  const dia = new Date(Date.now() + diasDesdeHoy * 86_400_000)
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(dia)
}

let dejarDeEscuchar: (() => void) | null = null

interface EstadoCompras {
  proyecto: string | null
  ordenes: OrdenCompraCable[]
  proveedores: ProveedorCable[]
  avisos: string[]
  /** true cuando lo mostrado viene del dispositivo y no del servidor */
  desdeDispositivo: boolean

  iniciar: (proyecto: string) => Promise<void>
  cargar: () => Promise<void>
  registrarProveedor: (datos: {
    nombre: string
    empresa?: string
    ruc?: string
    telefono?: string
    categoria?: string
  }) => Promise<ProveedorCable>
  crearPedido: (datos: {
    proveedor: ProveedorCable
    items: ItemNuevo[]
    fechaEstimada?: string
    borrador?: boolean
  }) => Promise<void>
  avanzar: (orden: string, estado: 'pendiente' | 'en_camino') => Promise<void>
  recibir: (orden: string, entradas: EntradaRecepcion[]) => Promise<void>
  cerrar: (orden: string) => Promise<void>
  descartarAviso: (indice: number) => void
}

export const useCompras = create<EstadoCompras>()((set, get) => {
  async function persistirOrdenes(ordenes: OrdenCompraCable[]) {
    const { proyecto } = get()
    if (!proyecto) return
    const base = baseDe(proyecto)
    await base.transaction('rw', base.ordenesCompra, async () => {
      await base.ordenesCompra.clear()
      await base.ordenesCompra.bulkPut(ordenes)
    })
  }

  function reemplazar(orden: OrdenCompraCable) {
    const ordenes = get().ordenes
    const siguiente =
      orden.estado === 'cerrada'
        ? ordenes.filter((o) => o.uuid !== orden.uuid)
        : ordenes.some((o) => o.uuid === orden.uuid)
          ? ordenes.map((o) => (o.uuid === orden.uuid ? orden : o))
          : [orden, ...ordenes]
    set({ ordenes: siguiente })
    void persistirOrdenes(siguiente)
  }

  function buscar(uuid: string): OrdenCompraCable | undefined {
    return get().ordenes.find((o) => o.uuid === uuid)
  }

  async function enviar(
    metodo: 'POST' | 'PATCH',
    ruta: string,
    descripcion: string,
    cuerpo?: Record<string, unknown>,
  ) {
    const { proyecto } = get()
    if (!proyecto) throw new Error('Sin proyecto activo')
    await encolar(proyecto, { metodo, ruta, descripcion, cuerpo })
  }

  return {
    proyecto: null,
    ordenes: [],
    proveedores: [],
    avisos: [],
    desdeDispositivo: false,

    iniciar: async (proyecto) => {
      if (get().proyecto !== proyecto) {
        set({ proyecto, ordenes: [], proveedores: [], avisos: [] })
        dejarDeEscuchar?.()
        dejarDeEscuchar = alAplicarOperacion(async (operacion, respuesta) => {
          if (!operacion.ruta.startsWith('/api/compras/')) return
          const resultado = respuesta as Partial<ResultadoOrdenCable> | undefined
          const orden = resultado?.orden
          if (!orden) return
          // Con más cambios de ese pedido por enviar, lo local sigue siendo lo más nuevo
          const pendientes = await baseDe(proyecto)
            .operaciones.where('estado')
            .equals('pendiente')
            .filter((op) => op.ruta.includes(orden.uuid))
            .count()
          if (pendientes === 0) reemplazar(orden)
          if (resultado.avisos?.length) set({ avisos: [...get().avisos, ...resultado.avisos] })
        })
      }
      await get().cargar()
    },

    cargar: async () => {
      const { proyecto } = get()
      if (!proyecto) return
      const base = baseDe(proyecto)
      const desdeDispositivo = async () =>
        set({
          ordenes: await base.ordenesCompra.toArray(),
          proveedores: await base.proveedores.orderBy('nombre').toArray(),
          desdeDispositivo: true,
        })
      // Con cambios sin enviar, lo del dispositivo es más nuevo que el servidor
      if (useSincronizacion.getState().pendientes > 0) return desdeDispositivo()
      try {
        const [ordenes, proveedores] = await Promise.all([
          pedir<OrdenCompraCable[]>(
            'GET',
            '/api/compras/ordenes?estado=borrador&estado=pendiente&estado=en_camino&estado=recibida',
          ),
          pedir<ProveedorCable[]>('GET', '/api/compras/proveedores?limite=200'),
        ])
        set({ ordenes, proveedores, desdeDispositivo: false })
        void persistirOrdenes(ordenes)
        await base.transaction('rw', base.proveedores, async () => {
          await base.proveedores.clear()
          await base.proveedores.bulkPut(proveedores)
        })
      } catch (error) {
        if (!(error instanceof SinConexion)) throw error
        await desdeDispositivo()
      }
    },

    registrarProveedor: async (datos) => {
      const { proyecto } = get()
      if (!proyecto) throw new Error('Sin proyecto activo')
      const proveedor: ProveedorCable = {
        uuid: crypto.randomUUID(),
        nombre: datos.nombre,
        empresa: datos.empresa || null,
        ruc: datos.ruc || null,
        telefono: datos.telefono || null,
        categoria: datos.categoria || null,
        creado_en: new Date().toISOString(),
      }
      const proveedores = [...get().proveedores, proveedor].sort((a, b) => a.nombre.localeCompare(b.nombre))
      set({ proveedores })
      await baseDe(proyecto).proveedores.put(proveedor)
      await enviar('POST', '/api/compras/proveedores', `Registrar a ${proveedor.nombre}`, {
        uuid: proveedor.uuid,
        nombre: proveedor.nombre,
        empresa: proveedor.empresa,
        ruc: proveedor.ruc,
        telefono: proveedor.telefono,
        categoria: proveedor.categoria,
      })
      return proveedor
    },

    crearPedido: async ({ proveedor, items, fechaEstimada, borrador }) => {
      const uuid = crypto.randomUUID()
      const conUuid = items.map((item) => ({ ...item, uuid: crypto.randomUUID() }))
      const total = items.reduce((suma, item) => suma + item.centimos, 0)
      const estado = borrador ? 'borrador' : 'pendiente'
      reemplazar({
        uuid,
        proveedor_uuid: proveedor.uuid,
        proveedor: proveedor.nombre,
        proveedor_telefono: proveedor.telefono,
        estado,
        fecha_estimada_llegada: fechaEstimada ?? null,
        monto_total: aSoles(total),
        monto_real: null,
        notas: null,
        items: conUuid.map((item) => ({
          uuid: item.uuid,
          nombre_producto: item.nombre,
          cantidad: item.cantidad || null,
          monto: aSoles(item.centimos),
          estado_recepcion: 'pendiente',
          producto_sustituto: null,
          monto_sustituto: null,
        })),
      })
      await enviar('POST', '/api/compras/ordenes', `Pedido a ${proveedor.nombre}`, {
        uuid,
        proveedor_uuid: proveedor.uuid,
        estado,
        fecha_estimada_llegada: fechaEstimada ?? null,
        items: conUuid.map((item) => ({
          uuid: item.uuid,
          nombre_producto: item.nombre,
          cantidad: item.cantidad || null,
          monto: aSoles(item.centimos),
        })),
      })
    },

    avanzar: async (uuid, estado) => {
      const orden = buscar(uuid)
      if (!orden) return
      reemplazar({ ...orden, estado })
      await enviar(
        'PATCH',
        `/api/compras/ordenes/${uuid}/estado`,
        estado === 'en_camino'
          ? `Pedido de ${orden.proveedor} en camino`
          : `Confirmar pedido a ${orden.proveedor}`,
        { estado },
      )
    },

    recibir: async (uuid, entradas) => {
      const orden = buscar(uuid)
      if (!orden) return
      reemplazar(aplicarRecepcion(orden, entradas))
      await enviar('POST', `/api/compras/ordenes/${uuid}/recepcion`, `Recibir pedido de ${orden.proveedor}`, {
        items: entradas.map((entrada) => ({
          item_uuid: entrada.itemUuid,
          estado: entrada.estado,
          producto_sustituto: entrada.productoSustituto ?? null,
          monto_sustituto:
            entrada.montoSustitutoCentimos === undefined ? null : aSoles(entrada.montoSustitutoCentimos),
          cantidad_stock: entrada.cantidadStock || null,
        })),
      })
    },

    cerrar: async (uuid) => {
      const orden = buscar(uuid)
      if (!orden) return
      reemplazar({ ...orden, estado: 'cerrada' })
      await enviar('POST', `/api/compras/ordenes/${uuid}/cerrar`, `Cerrar pedido de ${orden.proveedor}`)
    },

    descartarAviso: (indice) => set({ avisos: get().avisos.filter((_, i) => i !== indice) }),
  }
})
