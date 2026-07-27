/**
 * Datos ficticios de la Demo 1 (coherentes entre sí, ver README.md).
 * En demos siguientes este módulo leerá datos reales de Ventas y Compras
 * (IndexedDB vía Dexie, sincronizado con el backend).
 *
 * Las fechas se calculan respecto al día actual: el sistema detecta
 * fecha/hora/zona automáticamente, el usuario nunca las ingresa.
 */

export interface ResumenCaja {
  ventasHoy: number
  ventasCerradas: number
  proyeccionManana: number
  motivoProyeccion: string
}

export interface OrdenActiva {
  id: number
  nombre: string
  tipo: 'orden_activa' | 'fiado'
  monto: number
  /** Solo para fiado: deuda acumulada del cliente */
  deudaCliente?: number
}

export interface PedidoPorLlegar {
  id: number
  proveedor: string
  fechaEstimada: Date
  monto: number
}

export interface FiadosPorCobrar {
  total: number
  cantidadClientes: number
}

export interface VentasRapidasPendientes {
  cantidad: number
}

function dentroDeDias(dias: number): Date {
  const fecha = new Date()
  fecha.setDate(fecha.getDate() + dias)
  return fecha
}

export const resumenCaja: ResumenCaja = {
  ventasHoy: 485.5,
  ventasCerradas: 12,
  proyeccionManana: 320.0,
  motivoProyeccion: 'Llega pedido de Distribuidora Norte',
}

export const ordenesActivas: OrdenActiva[] = [
  { id: 1, nombre: 'Restaurante Doña Carmen', tipo: 'orden_activa', monto: 86.0 },
  { id: 2, nombre: 'Orden 2', tipo: 'orden_activa', monto: 23.5 },
  { id: 3, nombre: 'Sra. Flora', tipo: 'fiado', monto: 12.0, deudaCliente: 45.0 },
]

export const pedidosPorLlegar: PedidoPorLlegar[] = [
  { id: 1, proveedor: 'Distribuidora Norte', fechaEstimada: dentroDeDias(1), monto: 320.0 },
  { id: 2, proveedor: 'Avícola San Pedro', fechaEstimada: dentroDeDias(2), monto: 145.0 },
  // Un pedido que debió llegar ayer: el caso más común y el que nunca
  // debe mostrarse como "llega hoy"
  { id: 3, proveedor: 'Abarrotes El Sol', fechaEstimada: dentroDeDias(-1), monto: 88.0 },
]

export const fiadosPorCobrar: FiadosPorCobrar = {
  total: 132.5,
  cantidadClientes: 4,
}

export const ventasRapidasPendientes: VentasRapidasPendientes = {
  cantidad: 3,
}
