import { create } from 'zustand'
import { SinConexion, pedir } from '../../api/cliente'
import {
  aCentimos,
  aSoles,
  type ClienteCable,
  type MetodoPago,
  type ResultadoVentaCable,
  type VentaCable,
} from '../../api/contrato'
import { baseDe } from '../../sincronizacion/base-local'
import { alAplicarOperacion, encolar, useSincronizacion } from '../../sincronizacion/cola'

/**
 * Estado del módulo Ventas, offline-first (ADR-032).
 *
 * Cada acción del operador (1) cambia la pantalla al instante, (2) guarda
 * el cambio en IndexedDB y (3) lo encola para el servidor. Sin red la venta
 * sigue su curso; al volver la conexión la cola la entrega y la respuesta del
 * servidor (la verdad: totales, avisos) reemplaza a la versión local.
 */

const nuevoUuid = () => crypto.randomUUID()

function sumarItems(venta: VentaCable): VentaCable {
  if (venta.tipo === 'venta_rapida') return venta
  // Solo para mostrar al instante: el servidor recalcula y su total manda
  const centimos = venta.items.reduce((total, item) => total + aCentimos(item.monto), 0)
  return { ...venta, monto_total: aSoles(centimos) }
}

/** Suscripción a la cola del proyecto activo (se libera al cambiar de proyecto). */
let dejarDeEscuchar: (() => void) | null = null

interface EstadoVentas {
  proyecto: string | null
  abiertas: VentaCable[]
  /** Ventas rápidas cobradas a las que falta registrarles el detalle */
  rapidas: VentaCable[]
  seleccionada: string | null
  clientes: ClienteCable[]
  avisos: string[]
  cargando: boolean
  /** true cuando lo mostrado viene del dispositivo y no del servidor */
  desdeDispositivo: boolean

  iniciar: (proyecto: string) => Promise<void>
  cargar: () => Promise<void>
  seleccionar: (uuid: string) => void
  abrirOrden: (datos: { nombreOrden?: string; cliente?: ClienteCable }) => Promise<string>
  agregarItem: (venta: string, item: { nombre: string; cantidad?: string; centimos: number }) => Promise<void>
  quitarItem: (venta: string, item: string) => Promise<void>
  cobrar: (venta: string, metodo: MetodoPago) => Promise<void>
  fiar: (venta: string, cliente?: ClienteCable) => Promise<void>
  anular: (venta: string) => Promise<void>
  ventaRapida: (centimos: number, metodo: MetodoPago) => Promise<void>
  cargarRapidas: () => Promise<void>
  formalizar: (venta: string) => Promise<void>
  buscarClientes: (texto: string) => Promise<void>
  crearCliente: (nombre: string, telefono?: string) => Promise<ClienteCable>
  descartarAviso: (indice: number) => void
}

export const useVentas = create<EstadoVentas>()((set, get) => {
  /** Guarda en el dispositivo lo que se ve, para abrir la app sin red. */
  async function persistir(abiertas: VentaCable[]) {
    const { proyecto } = get()
    if (!proyecto) return
    const base = baseDe(proyecto)
    await base.transaction('rw', base.ventasAbiertas, async () => {
      await base.ventasAbiertas.clear()
      await base.ventasAbiertas.bulkPut(abiertas)
    })
  }

  function reemplazar(venta: VentaCable) {
    if (venta.tipo === 'venta_rapida') {
      const rapidas = get().rapidas
      set({
        rapidas:
          venta.estado === 'pendiente_formalizar'
            ? rapidas.some((v) => v.uuid === venta.uuid)
              ? rapidas.map((v) => (v.uuid === venta.uuid ? venta : v))
              : [...rapidas, venta]
            : rapidas.filter((v) => v.uuid !== venta.uuid),
      })
      return
    }
    const abiertas = get().abiertas
    const siguiente =
      venta.estado === 'abierta'
        ? abiertas.some((v) => v.uuid === venta.uuid)
          ? abiertas.map((v) => (v.uuid === venta.uuid ? venta : v))
          : [...abiertas, venta]
        : abiertas.filter((v) => v.uuid !== venta.uuid)
    set({
      abiertas: siguiente,
      seleccionada: siguiente.some((v) => v.uuid === get().seleccionada)
        ? get().seleccionada
        : (siguiente[0]?.uuid ?? null),
    })
    void persistir(siguiente)
  }

  function quitarDelPanel(uuid: string) {
    const siguiente = get().abiertas.filter((v) => v.uuid !== uuid)
    set({
      abiertas: siguiente,
      seleccionada: get().seleccionada === uuid ? (siguiente[0]?.uuid ?? null) : get().seleccionada,
    })
    void persistir(siguiente)
  }

  function cambiarLocal(uuid: string, cambio: (venta: VentaCable) => VentaCable) {
    const venta = [...get().abiertas, ...get().rapidas].find((v) => v.uuid === uuid)
    if (venta) reemplazar(cambio(venta))
  }

  async function enviar(
    metodo: 'POST' | 'DELETE' | 'PATCH',
    ruta: string,
    descripcion: string,
    cuerpo?: Record<string, unknown>,
  ) {
    const { proyecto } = get()
    if (!proyecto) throw new Error('Sin proyecto activo')
    await encolar(proyecto, { metodo, ruta, descripcion, cuerpo })
  }

  /** El mismo nombre que ve el operador en la pestaña ("Orden 2") */
  function nombreDe(venta: VentaCable | undefined): string {
    if (!venta) return 'la orden'
    const posicion = get().abiertas.findIndex((v) => v.uuid === venta.uuid) + 1
    return venta.cliente_nombre ?? venta.nombre_orden ?? `Orden ${posicion}`
  }

  return {
    proyecto: null,
    abiertas: [],
    rapidas: [],
    seleccionada: null,
    clientes: [],
    avisos: [],
    cargando: false,
    desdeDispositivo: false,

    iniciar: async (proyecto) => {
      if (get().proyecto === proyecto) return
      set({ proyecto, abiertas: [], rapidas: [], seleccionada: null, avisos: [] })
      // La respuesta del servidor manda, salvo que aún haya cambios de esa
      // venta por enviar (si no, se borrarían de la pantalla un momento)
      dejarDeEscuchar?.()
      dejarDeEscuchar = alAplicarOperacion(async (_operacion, respuesta) => {
        const resultado = respuesta as Partial<ResultadoVentaCable> | undefined
        const venta = resultado?.venta
        if (!venta) return
        const pendientes = await baseDe(proyecto)
          .operaciones.where('estado')
          .equals('pendiente')
          .filter((op) => op.ruta.includes(venta.uuid))
          .count()
        if (pendientes === 0) reemplazar(venta)
        if (resultado.avisos?.length) set({ avisos: [...get().avisos, ...resultado.avisos] })
      })
      await get().cargar()
    },

    cargar: async () => {
      const { proyecto } = get()
      if (!proyecto) return
      set({ cargando: true })
      const base = baseDe(proyecto)
      const locales = await base.ventasAbiertas.toArray()
      // Con cambios sin enviar, lo del dispositivo es más nuevo que el servidor
      if (useSincronizacion.getState().pendientes > 0) {
        set({ abiertas: locales, desdeDispositivo: true, cargando: false })
      } else {
        try {
          const abiertas = await pedir<VentaCable[]>('GET', '/api/ventas/abiertas')
          set({ abiertas, desdeDispositivo: false })
          void persistir(abiertas)
        } catch (error) {
          if (!(error instanceof SinConexion)) throw error
          set({ abiertas: locales, desdeDispositivo: true })
        } finally {
          set({ cargando: false })
        }
      }
      const { abiertas, seleccionada } = get()
      if (!abiertas.some((v) => v.uuid === seleccionada)) set({ seleccionada: abiertas[0]?.uuid ?? null })
    },

    seleccionar: (uuid) => set({ seleccionada: uuid }),

    abrirOrden: async ({ nombreOrden, cliente }) => {
      const uuid = nuevoUuid()
      const tipo = cliente ? 'fiado' : 'orden_activa'
      const posicion = get().abiertas.length + 1
      reemplazar({
        uuid,
        tipo,
        cliente_uuid: cliente?.uuid ?? null,
        cliente_nombre: cliente?.nombre ?? null,
        nombre_orden: nombreOrden || null,
        estado: 'abierta',
        monto_total: '0.00',
        metodo_pago: null,
        abierta_en: new Date().toISOString(),
        cerrada_en: null,
        items: [],
        deuda_cliente: null,
      })
      set({ seleccionada: uuid })
      await enviar('POST', '/api/ventas/', `Abrir ${cliente?.nombre ?? nombreOrden ?? `Orden ${posicion}`}`, {
        uuid,
        tipo,
        cliente_uuid: cliente?.uuid,
        nombre_orden: nombreOrden || undefined,
      })
      return uuid
    },

    agregarItem: async (ventaUuid, { nombre, cantidad, centimos }) => {
      const uuid = nuevoUuid()
      const monto = aSoles(centimos)
      cambiarLocal(ventaUuid, (venta) =>
        sumarItems({
          ...venta,
          items: [
            ...venta.items,
            {
              uuid,
              nombre_producto: nombre,
              cantidad: cantidad || null,
              monto,
              producto_uuid: null,
              cantidad_num: null,
            },
          ],
        }),
      )
      await enviar('POST', `/api/ventas/${ventaUuid}/items`, `Agregar ${nombre}`, {
        uuid,
        nombre_producto: nombre,
        cantidad: cantidad || undefined,
        monto,
      })
    },

    quitarItem: async (ventaUuid, itemUuid) => {
      const venta = get().abiertas.find((v) => v.uuid === ventaUuid)
      const item = venta?.items.find((i) => i.uuid === itemUuid)
      cambiarLocal(ventaUuid, (v) => sumarItems({ ...v, items: v.items.filter((i) => i.uuid !== itemUuid) }))
      await enviar(
        'DELETE',
        `/api/ventas/${ventaUuid}/items/${itemUuid}`,
        `Quitar ${item?.nombre_producto ?? 'producto'}`,
      )
    },

    cobrar: async (ventaUuid, metodo) => {
      // El nombre se toma ANTES de sacar la venta del panel (cambia la posición)
      const descripcion = `Cobrar ${nombreDe(get().abiertas.find((v) => v.uuid === ventaUuid))}`
      cambiarLocal(ventaUuid, (v) => ({ ...v, estado: 'pagada_cerrada', metodo_pago: metodo }))
      await enviar('POST', `/api/ventas/${ventaUuid}/cobrar`, descripcion, {
        metodo_pago: metodo,
      })
    },

    fiar: async (ventaUuid, cliente) => {
      const descripcion = `Fiar a ${cliente?.nombre ?? nombreDe(get().abiertas.find((v) => v.uuid === ventaUuid))}`
      cambiarLocal(ventaUuid, (v) => ({ ...v, estado: 'fiada', tipo: 'fiado' }))
      await enviar('POST', `/api/ventas/${ventaUuid}/fiar`, descripcion, {
        cliente_uuid: cliente?.uuid,
      })
    },

    anular: async (ventaUuid) => {
      const descripcion = `Anular ${nombreDe(get().abiertas.find((v) => v.uuid === ventaUuid))}`
      quitarDelPanel(ventaUuid)
      await enviar('DELETE', `/api/ventas/${ventaUuid}`, descripcion)
    },

    ventaRapida: async (centimos, metodo) => {
      const monto = aSoles(centimos)
      await enviar('POST', '/api/ventas/', `Venta rápida de S/ ${monto}`, {
        uuid: nuevoUuid(),
        tipo: 'venta_rapida',
        monto,
        metodo_pago: metodo,
      })
      set({
        avisos: [
          ...get().avisos,
          `Venta rápida de S/ ${monto} registrada. Complétala cuando tengas un momento.`,
        ],
      })
    },

    cargarRapidas: async () => {
      try {
        const rapidas = await pedir<VentaCable[]>('GET', '/api/ventas/?estado=pendiente_formalizar&limite=50')
        set({ rapidas })
      } catch (error) {
        if (!(error instanceof SinConexion)) throw error
        // Sin red se completan después: no hay nada urgente que mostrar
      }
    },

    formalizar: async (ventaUuid) => {
      set({ rapidas: get().rapidas.filter((v) => v.uuid !== ventaUuid) })
      await enviar('POST', `/api/ventas/${ventaUuid}/formalizar`, 'Completar el detalle de una venta rápida')
    },

    buscarClientes: async (texto) => {
      const { proyecto } = get()
      if (!proyecto) return
      const base = baseDe(proyecto)
      try {
        const clientes = await pedir<ClienteCable[]>(
          'GET',
          `/api/ventas/clientes?buscar=${encodeURIComponent(texto)}&limite=20`,
        )
        await base.clientes.bulkPut(clientes)
        set({ clientes })
      } catch (error) {
        if (!(error instanceof SinConexion)) throw error
        const buscado = texto.trim().toLowerCase()
        const locales = await base.clientes.toArray()
        set({ clientes: locales.filter((c) => c.nombre.toLowerCase().includes(buscado)).slice(0, 20) })
      }
    },

    crearCliente: async (nombre, telefono) => {
      const cliente: ClienteCable = {
        uuid: nuevoUuid(),
        nombre,
        telefono: telefono || null,
        limite_credito: null,
        creado_en: new Date().toISOString(),
      }
      const { proyecto } = get()
      if (proyecto) await baseDe(proyecto).clientes.put(cliente)
      set({ clientes: [cliente, ...get().clientes] })
      await enviar('POST', '/api/ventas/clientes', `Registrar cliente ${nombre}`, {
        uuid: cliente.uuid,
        nombre,
        telefono: telefono || undefined,
      })
      return cliente
    },

    descartarAviso: (indice) => set({ avisos: get().avisos.filter((_, i) => i !== indice) }),
  }
})
