import { create } from 'zustand'
import { SinConexion, pedir } from '../../api/cliente'
import type { ProductoCable, Unidad } from '../../api/contrato'
import { baseDe } from '../../sincronizacion/base-local'
import { alAplicarOperacion, encolar, useSincronizacion } from '../../sincronizacion/cola'

/**
 * Estado del módulo Inventario, offline-first como Ventas y Compras (ADR-032). El stock
 * que manda es el del servidor (Σ movimientos, ADR-031); aquí solo se refleja al instante
 * lo que el operador acaba de hacer, mientras la cola lo entrega.
 */

const PATRON_CANTIDAD = /^(-)?(\d+)(?:\.(\d{1,3}))?$/

/** "5.250" → 5250 milésimas. Cantidades exactas, igual que el dinero en céntimos. */
export function aMilesimas(texto: string): number {
  const partes = PATRON_CANTIDAD.exec(texto.trim())
  if (!partes) throw new Error(`Cantidad inválida desde el servidor: "${texto}"`)
  const [, signo, enteros, decimales = ''] = partes
  const valor = Number(enteros) * 1000 + Number(decimales.padEnd(3, '0'))
  return signo ? -valor : valor
}

/** 5250 → "5.25", para enviar al servidor. */
export function aCantidad(milesimas: number): string {
  const signo = milesimas < 0 ? '-' : ''
  const absoluto = Math.abs(milesimas)
  const decimales = String(absoluto % 1000)
    .padStart(3, '0')
    .replace(/0+$/, '')
  return `${signo}${Math.floor(absoluto / 1000)}${decimales ? `.${decimales}` : ''}`
}

/** Lo que escribe el operador ("2", "1,5", "0.250") → milésimas, o null si no es una cantidad. */
export function leerCantidadEscrita(texto: string): number | null {
  const limpio = texto.trim().replace(',', '.')
  if (!/^\d+(\.\d{1,3})?$/.test(limpio)) return null
  return aMilesimas(limpio)
}

const NOMBRE_UNIDAD: Record<Unidad, [string, string]> = {
  unidad: ['unidad', 'unidades'],
  kg: ['kg', 'kg'],
  litro: ['litro', 'litros'],
}

/** 5250, "kg" → "5.25 kg". La coma o el punto los pone el operador; aquí se muestra con punto. */
export function formatearCantidad(milesimas: number, unidad: Unidad): string {
  const [singular, plural] = NOMBRE_UNIDAD[unidad]
  return `${aCantidad(milesimas)} ${milesimas === 1000 ? singular : plural}`
}

/**
 * Monto de una venta por cantidad: precio (céntimos por unidad, kg o litro) × milésimas.
 * Redondea al céntimo, como el vendedor lo cobraría. Solo sugiere: el operador puede cambiarlo.
 */
export function montoPorCantidad(precioCentimos: number, milesimas: number): number {
  return Math.round((precioCentimos * milesimas) / 1000)
}

/** Igual que `_con_estado` del backend: la pantalla lo dice con palabras al instante. */
export function conEstado(producto: ProductoCable): ProductoCable {
  const stock = aMilesimas(producto.stock_actual)
  const minimo = producto.stock_minimo === null ? null : aMilesimas(producto.stock_minimo)
  return { ...producto, bajo_minimo: minimo !== null && stock <= minimo, descuadre: stock < 0 }
}

let dejarDeEscuchar: (() => void) | null = null

interface EstadoInventario {
  proyecto: string | null
  productos: ProductoCable[]
  /** true cuando lo mostrado viene del dispositivo y no del servidor */
  desdeDispositivo: boolean

  iniciar: (proyecto: string) => Promise<void>
  cargar: () => Promise<void>
  crear: (datos: {
    nombre: string
    unidad: Unidad
    precioVenta?: string
    stockInicial?: number
    stockMinimo?: number
    tieneVencimiento: boolean
  }) => Promise<void>
  editar: (uuid: string, cambios: { precioVenta?: string; stockMinimo?: number }) => Promise<void>
  contar: (uuid: string, contado: number) => Promise<void>
  merma: (uuid: string, cantidad: number, nota?: string) => Promise<void>
  /**
   * Refleja al instante lo que movió OTRO módulo (una venta). No encola nada: el
   * movimiento real lo hace el servidor por evento al recibir la venta (ADR-031).
   */
  ajustarLocal: (uuid: string, deltaMilesimas: number) => void
}

export const useInventario = create<EstadoInventario>()((set, get) => {
  async function persistir(productos: ProductoCable[]) {
    const { proyecto } = get()
    if (!proyecto) return
    const base = baseDe(proyecto)
    await base.transaction('rw', base.productos, async () => {
      await base.productos.clear()
      await base.productos.bulkPut(productos)
    })
  }

  function reemplazar(producto: ProductoCable) {
    const productos = get().productos
    const siguiente = (
      productos.some((p) => p.uuid === producto.uuid)
        ? productos.map((p) => (p.uuid === producto.uuid ? producto : p))
        : [...productos, producto]
    ).sort((a, b) => a.nombre.localeCompare(b.nombre))
    set({ productos: siguiente })
    void persistir(siguiente)
  }

  function cambiarLocal(uuid: string, cambio: (producto: ProductoCable) => ProductoCable) {
    const producto = get().productos.find((p) => p.uuid === uuid)
    if (producto) reemplazar(conEstado(cambio(producto)))
    return producto
  }

  async function enviar(
    metodo: 'POST' | 'PATCH',
    ruta: string,
    descripcion: string,
    cuerpo: Record<string, unknown>,
  ) {
    const { proyecto } = get()
    if (!proyecto) throw new Error('Sin proyecto activo')
    await encolar(proyecto, { metodo, ruta, descripcion, cuerpo })
  }

  return {
    proyecto: null,
    productos: [],
    desdeDispositivo: false,

    iniciar: async (proyecto) => {
      if (get().proyecto !== proyecto) {
        set({ proyecto, productos: [] })
        dejarDeEscuchar?.()
        dejarDeEscuchar = alAplicarOperacion(async (operacion, respuesta) => {
          if (!operacion.ruta.startsWith('/api/inventario/')) return
          // Ajuste responde {producto, diferencia}; lo demás, el producto
          const datos = respuesta as { producto?: ProductoCable } & Partial<ProductoCable>
          const producto = datos?.producto ?? (datos?.uuid ? (datos as ProductoCable) : undefined)
          if (!producto) return
          const pendientes = await baseDe(proyecto)
            .operaciones.where('estado')
            .equals('pendiente')
            .filter((op) => op.cuerpo?.producto_uuid === producto.uuid || op.ruta.includes(producto.uuid))
            .count()
          if (pendientes === 0) reemplazar(conEstado(producto))
        })
      }
      await get().cargar()
    },

    cargar: async () => {
      const { proyecto } = get()
      if (!proyecto) return
      const base = baseDe(proyecto)
      const desdeDispositivo = async () =>
        set({ productos: await base.productos.orderBy('nombre').toArray(), desdeDispositivo: true })
      // Con cambios sin enviar, lo del dispositivo es más nuevo que el servidor
      if (useSincronizacion.getState().pendientes > 0) return desdeDispositivo()
      try {
        const productos = await pedir<ProductoCable[]>('GET', '/api/inventario/productos?limite=500')
        set({ productos, desdeDispositivo: false })
        void persistir(productos)
      } catch (error) {
        if (!(error instanceof SinConexion)) throw error
        await desdeDispositivo()
      }
    },

    crear: async ({ nombre, unidad, precioVenta, stockInicial, stockMinimo, tieneVencimiento }) => {
      const uuid = crypto.randomUUID()
      reemplazar(
        conEstado({
          uuid,
          nombre,
          unidad,
          precio_venta: precioVenta ?? null,
          stock_actual: aCantidad(stockInicial ?? 0),
          stock_minimo: stockMinimo === undefined ? null : aCantidad(stockMinimo),
          codigo_barras: null,
          tiene_vencimiento: tieneVencimiento,
          bajo_minimo: false,
          descuadre: false,
        }),
      )
      await enviar('POST', '/api/inventario/productos', `Registrar ${nombre}`, {
        uuid,
        nombre,
        unidad,
        precio_venta: precioVenta ?? null,
        stock_inicial: stockInicial === undefined ? null : aCantidad(stockInicial),
        stock_minimo: stockMinimo === undefined ? null : aCantidad(stockMinimo),
        tiene_vencimiento: tieneVencimiento,
      })
    },

    editar: async (uuid, { precioVenta, stockMinimo }) => {
      const producto = cambiarLocal(uuid, (p) => ({
        ...p,
        precio_venta: precioVenta ?? p.precio_venta,
        stock_minimo: stockMinimo === undefined ? p.stock_minimo : aCantidad(stockMinimo),
      }))
      if (!producto) return
      const cuerpo: Record<string, unknown> = {}
      if (precioVenta !== undefined) cuerpo.precio_venta = precioVenta
      if (stockMinimo !== undefined) cuerpo.stock_minimo = aCantidad(stockMinimo)
      await enviar(
        'PATCH',
        `/api/inventario/productos/${uuid}`,
        `Cambiar datos de ${producto.nombre}`,
        cuerpo,
      )
    },

    contar: async (uuid, contado) => {
      // El servidor calcula la diferencia contra el stock de ESE momento (ADR-031)
      const producto = cambiarLocal(uuid, (p) => ({ ...p, stock_actual: aCantidad(contado) }))
      if (!producto) return
      await enviar('POST', '/api/inventario/ajustes', `Conteo de ${producto.nombre}`, {
        uuid: crypto.randomUUID(),
        producto_uuid: uuid,
        contado: aCantidad(contado),
      })
    },

    merma: async (uuid, cantidad, nota) => {
      const producto = cambiarLocal(uuid, (p) => ({
        ...p,
        stock_actual: aCantidad(aMilesimas(p.stock_actual) - cantidad),
      }))
      if (!producto) return
      await enviar('POST', '/api/inventario/mermas', `Merma de ${producto.nombre}`, {
        uuid: crypto.randomUUID(),
        producto_uuid: uuid,
        cantidad: aCantidad(cantidad),
        nota: nota || null,
      })
    },

    ajustarLocal: (uuid, deltaMilesimas) => {
      cambiarLocal(uuid, (p) => ({
        ...p,
        stock_actual: aCantidad(aMilesimas(p.stock_actual) + deltaMilesimas),
      }))
    },
  }
})
