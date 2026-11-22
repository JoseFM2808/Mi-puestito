/**
 * Contrato con el backend (ADR-033). ÚNICA frontera de conversión:
 *
 * - En el cable: snake_case y dinero como string decimal ("485.50").
 * - En la app: camelCase y dinero en CÉNTIMOS ENTEROS (48550). Sumar
 *   céntimos es exacto; sumar floats no (0.1 + 0.2 ≠ 0.3).
 *
 * Guarda contra desalineamiento: cada interfaz "Cable" tiene una lista de
 * campos que TypeScript obliga a ser exacta, y `contrato.test.ts` compara
 * esa lista con `openapi.json`, que a su vez un test del backend compara con
 * el API real. Si alguien cambia un esquema de un lado, falla un test.
 */

// ------------------------------------------------------------------ dinero

const PATRON_DINERO = /^(-)?(\d+)(?:\.(\d{1,2}))?$/

/** "485.50" → 48550. Lanza si el texto no es un monto (nunca adivina). */
export function aCentimos(texto: string): number {
  const partes = PATRON_DINERO.exec(texto.trim())
  if (!partes) throw new Error(`Monto inválido desde el servidor: "${texto}"`)
  const [, signo, enteros, decimales = ''] = partes
  const valor = Number(enteros) * 100 + Number(decimales.padEnd(2, '0'))
  return signo ? -valor : valor
}

/** 48550 → "485.50", para enviar al servidor. */
export function aSoles(centimos: number): string {
  if (!Number.isInteger(centimos)) throw new Error('Los céntimos deben ser enteros')
  const signo = centimos < 0 ? '-' : ''
  const absoluto = Math.abs(centimos)
  return `${signo}${Math.floor(absoluto / 100)}.${String(absoluto % 100).padStart(2, '0')}`
}

/**
 * Lo que la persona escribe ("12", "12.5", "12,50") → céntimos, o null si
 * no es un monto válido. En Perú se usa punto, pero la coma aparece.
 */
export function leerMontoEscrito(texto: string): number | null {
  const limpio = texto.trim().replace(',', '.')
  if (!/^\d+(\.\d{1,2})?$/.test(limpio)) return null
  return aCentimos(limpio)
}

const formatoMoneda = new Intl.NumberFormat('es-PE', {
  style: 'currency',
  currency: 'PEN',
  minimumFractionDigits: 2,
})

/** 48550 → "S/ 485.50". La división es solo para mostrar, nunca para calcular. */
export function formatearCentimos(centimos: number): string {
  return formatoMoneda.format(centimos / 100)
}

// ------------------------------------------------------------------ utilidades de tipo

/** Garantiza en compilación que `campos` lista EXACTAMENTE las claves de T. */
function camposDe<T>() {
  return <const K extends readonly (keyof T)[]>(
    campos: K & (Exclude<keyof T, K[number]> extends never ? unknown : ['Falta un campo del contrato']),
  ) => campos
}

// ------------------------------------------------------------------ sesión

export interface IngresoCable {
  token: string
  proyecto: string
  nombre_proyecto: string
  es_real: boolean
}

export interface CuentaVisibleCable {
  nombre_usuario: string
  nombre_proyecto: string
  es_real: boolean
}

// ------------------------------------------------------------------ dashboard

interface OrdenActivaResumenCable {
  uuid: string
  nombre: string
  tipo: string
  monto: string
  deuda_cliente: string | null
}

interface PedidoPorLlegarCable {
  uuid: string
  proveedor: string
  fecha_estimada: string
  monto: string
}

export interface ResumenDashboardCable {
  ventas_hoy: string
  ventas_cerradas: number
  proyeccion_manana: string
  motivo_proyeccion: string
  ordenes_activas: OrdenActivaResumenCable[]
  fiados_por_cobrar: string
  clientes_con_fiado: number
  ventas_rapidas_pendientes: number
  pedidos_por_llegar: PedidoPorLlegarCable[]
  productos_por_vencer: number
  secciones_no_disponibles: string[]
}

export interface ResumenCaja {
  ventasHoy: number
  ventasCerradas: number
  proyeccionManana: number
  motivoProyeccion: string
  ordenesActivas: {
    uuid: string
    nombre: string
    tipo: 'orden_activa' | 'fiado'
    monto: number
    deudaCliente: number | null
  }[]
  fiadosPorCobrar: number
  clientesConFiado: number
  ventasRapidasPendientes: number
  pedidosPorLlegar: { uuid: string; proveedor: string; fechaEstimada: Date; monto: number }[]
  /** Productos con stock que vencen esta semana o ya vencieron (D-22) */
  productosPorVencer: number
  seccionesNoDisponibles: string[]
}

/** "2026-09-28" como fecha del calendario peruano (mediodía de Lima: nunca cambia de día). */
function fechaPeruana(texto: string): Date {
  return new Date(`${texto}T12:00:00-05:00`)
}

export function leerResumen(cable: ResumenDashboardCable): ResumenCaja {
  return {
    ventasHoy: aCentimos(cable.ventas_hoy),
    ventasCerradas: cable.ventas_cerradas,
    proyeccionManana: aCentimos(cable.proyeccion_manana),
    motivoProyeccion: cable.motivo_proyeccion,
    ordenesActivas: cable.ordenes_activas.map((orden) => ({
      uuid: orden.uuid,
      nombre: orden.nombre,
      tipo: orden.tipo === 'fiado' ? 'fiado' : 'orden_activa',
      monto: aCentimos(orden.monto),
      deudaCliente: orden.deuda_cliente === null ? null : aCentimos(orden.deuda_cliente),
    })),
    fiadosPorCobrar: aCentimos(cable.fiados_por_cobrar),
    clientesConFiado: cable.clientes_con_fiado,
    ventasRapidasPendientes: cable.ventas_rapidas_pendientes,
    pedidosPorLlegar: cable.pedidos_por_llegar.map((pedido) => ({
      uuid: pedido.uuid,
      proveedor: pedido.proveedor,
      fechaEstimada: fechaPeruana(pedido.fecha_estimada),
      monto: aCentimos(pedido.monto),
    })),
    productosPorVencer: cable.productos_por_vencer,
    seccionesNoDisponibles: cable.secciones_no_disponibles,
  }
}

// ------------------------------------------------------------------ ventas

export type TipoVenta = 'orden_activa' | 'fiado' | 'venta_rapida'
export type EstadoVenta = 'abierta' | 'pagada_cerrada' | 'fiada' | 'pendiente_formalizar'
export type MetodoPago = 'efectivo' | 'yape_plin'

export interface ItemVentaCable {
  uuid: string
  nombre_producto: string
  cantidad: string | null
  monto: string
  producto_uuid: string | null
  cantidad_num: string | null
}

export interface VentaCable {
  uuid: string
  tipo: TipoVenta
  cliente_uuid: string | null
  cliente_nombre: string | null
  nombre_orden: string | null
  estado: EstadoVenta
  monto_total: string
  metodo_pago: MetodoPago | null
  abierta_en: string
  cerrada_en: string | null
  items: ItemVentaCable[]
  deuda_cliente: string | null
}

export interface ResultadoVentaCable {
  venta: VentaCable
  avisos: string[]
}

export interface ItemVenta {
  uuid: string
  nombreProducto: string
  cantidad: string | null
  monto: number
}

export interface Venta {
  uuid: string
  tipo: TipoVenta
  clienteUuid: string | null
  clienteNombre: string | null
  nombreOrden: string | null
  estado: EstadoVenta
  montoTotal: number
  metodoPago: MetodoPago | null
  abiertaEn: string
  items: ItemVenta[]
  deudaCliente: number | null
}

export function leerVenta(cable: VentaCable): Venta {
  return {
    uuid: cable.uuid,
    tipo: cable.tipo,
    clienteUuid: cable.cliente_uuid,
    clienteNombre: cable.cliente_nombre,
    nombreOrden: cable.nombre_orden,
    estado: cable.estado,
    montoTotal: aCentimos(cable.monto_total),
    metodoPago: cable.metodo_pago,
    abiertaEn: cable.abierta_en,
    items: cable.items.map((item) => ({
      uuid: item.uuid,
      nombreProducto: item.nombre_producto,
      cantidad: item.cantidad,
      monto: aCentimos(item.monto),
    })),
    deudaCliente: cable.deuda_cliente === null ? null : aCentimos(cable.deuda_cliente),
  }
}

export interface ClienteCable {
  uuid: string
  nombre: string
  telefono: string | null
  limite_credito: string | null
  creado_en: string
}

export interface ClienteConDeudaCable extends ClienteCable {
  deuda: string
}

export interface Cliente {
  uuid: string
  nombre: string
  telefono: string | null
  limiteCredito: number | null
  deuda: number | null
}

export function leerCliente(cable: ClienteCable | ClienteConDeudaCable): Cliente {
  return {
    uuid: cable.uuid,
    nombre: cable.nombre,
    telefono: cable.telefono,
    limiteCredito: cable.limite_credito === null ? null : aCentimos(cable.limite_credito),
    deuda: 'deuda' in cable ? aCentimos(cable.deuda) : null,
  }
}

/** Cliente de la lista de fiados: su deuda siempre viene calculada. */
export function leerClienteConDeuda(cable: ClienteConDeudaCable): Cliente & { deuda: number } {
  return { ...leerCliente(cable), deuda: aCentimos(cable.deuda) }
}

export interface AbonoCable {
  uuid: string
  cliente_uuid: string
  monto: string
  metodo_pago: MetodoPago
  creado_en: string
  deuda_restante: string
  avisos: string[]
}

// ------------------------------------------------------------------ asistente

export interface AccionSugeridaCable {
  /** "ir_a" abre una pantalla; "resaltar" además señala una parte de ella (ADR-047) */
  tipo: 'ir_a' | 'resaltar'
  pantalla: string
  etiqueta: string
  /** El operador pidió ir o hacer algo: la app abre la pantalla sola (ADR-047) */
  automatica: boolean
  /** Solo en "resaltar": el data-ai-id de la parte que se señala */
  apartado: string | null
}

/** Un producto de la orden que el Asistente llenó (ADR-049) */
export interface ItemBorradorCable {
  nombre: string
  /** Decimal en texto ("2", "1.5") */
  cantidad: string
  /** Precio de UNA unidad, solo si el operador lo dijo */
  precio: string | null
}

/** Orden que el Asistente llenó; el operador la revisa y la guarda (ADR-049) */
export interface BorradorVentaCable {
  items: ItemBorradorCable[]
  /** Para quién es ("Sra. Bertha"), si el operador lo dijo: el nombre de la orden */
  para: string | null
}

/** Un pago de fiado, un gasto o una merma que el Asistente llenó; el operador lo guarda (D-28) */
export interface FormularioLlenadoCable {
  tipo: 'abono' | 'gasto' | 'merma'
  cliente: string | null
  producto: string | null
  /** Solo si el operador lo dijo */
  monto: string | null
  cantidad: string | null
  medio: 'efectivo' | 'yape_plin' | null
  ambito: 'puesto' | 'hogar' | null
  categoria: string | null
  nota: string | null
}

export interface RespuestaAsistenteCable {
  respuesta: string
  acciones: AccionSugeridaCable[]
  borrador: BorradorVentaCable | null
  formulario: FormularioLlenadoCable | null
  /** Lo que guardó en su memoria con esta respuesta (D-26) */
  recordado: string[]
  id_respuesta: string
  modelo: string
}

/** Un hecho que el Asistente recuerda del negocio; el operador lo puede olvidar (D-26) */
export interface RecuerdoCable {
  uuid: string
  texto: string
  creado_en: string
}

// ------------------------------------------------------------------ listas exactas de campos

// ------------------------------------------------------------------ compras

export type EstadoOrden = 'borrador' | 'pendiente' | 'en_camino' | 'recibida' | 'cerrada'
export type EstadoRecepcion = 'pendiente' | 'recibido' | 'no_recibido' | 'cambiado'

export interface ProveedorCable {
  uuid: string
  nombre: string
  empresa: string | null
  ruc: string | null
  telefono: string | null
  categoria: string | null
  creado_en: string
}

export interface ItemOrdenCompraCable {
  uuid: string
  nombre_producto: string
  cantidad: string | null
  monto: string
  estado_recepcion: EstadoRecepcion
  producto_sustituto: string | null
  monto_sustituto: string | null
}

export interface OrdenCompraCable {
  uuid: string
  proveedor_uuid: string
  proveedor: string
  proveedor_telefono: string | null
  estado: EstadoOrden
  fecha_estimada_llegada: string | null
  monto_total: string
  monto_real: string | null
  notas: string | null
  items: ItemOrdenCompraCable[]
}

export interface ResultadoOrdenCable {
  orden: OrdenCompraCable
  avisos: string[]
}

export interface ProductoFrecuenteCable {
  nombre_producto: string
  cantidad: string | null
  monto: string
  veces: number
}

// ------------------------------------------------------------------ inventario

export type Unidad = 'unidad' | 'kg' | 'litro'

/** Cantidades como string decimal con 3 decimales ("5.250"); el frontend las lleva en milésimas. */
export interface ProductoCable {
  uuid: string
  nombre: string
  unidad: Unidad
  precio_venta: string | null
  stock_actual: string
  stock_minimo: string | null
  codigo_barras: string | null
  tiene_vencimiento: boolean
  /** Lo que costó UNA unidad (kg, litro) en la última compra recibida (D-22) */
  costo_ultimo: string | null
  /** "2026-11-24": cuándo vence lo más antiguo que queda (D-22) */
  vence_el: string | null
  bajo_minimo: boolean
  descuadre: boolean
  /** Vence en 7 días o menos (o ya venció) y aún queda stock */
  vence_pronto: boolean
  vencido: boolean
}

export interface MovimientoCable {
  delta: string
  motivo: 'venta' | 'anulacion_venta' | 'compra' | 'ajuste' | 'merma'
  origen_tipo: string
  nota: string | null
  creado_en: string
}

// ------------------------------------------------------------------ asistente

export interface EstadoAsistenteCable {
  listo: boolean
  puede_guardar_llave: boolean
  llave_guardada: boolean
}

/** Esquema del backend (nombre en openapi.json) → campos que el frontend espera. */
// ------------------------------------------------------------------ caja y gastos (D-24, ADR-051)

/** De dónde entra o sale el dinero: la gaveta o el Yape */
export type MedioPago = 'efectivo' | 'yape_plin'

export interface SaldoPorMedioCable {
  efectivo: string
  yape_plin: string
}

export interface CajaDelDiaCable {
  dia: string
  abierta: boolean
  inicial: SaldoPorMedioCable
  ingresos: SaldoPorMedioCable
  egresos: SaldoPorMedioCable
  en_caja: SaldoPorMedioCable
  no_disponibles: string[]
}

export type AmbitoGasto = 'puesto' | 'hogar'
export type CategoriaGasto =
  'proveedor' | 'alquiler' | 'servicios' | 'transporte' | 'alimentacion' | 'educacion' | 'otros'

export interface GastoCable {
  uuid: string
  monto: string
  medio: MedioPago
  ambito: AmbitoGasto
  categoria: CategoriaGasto
  descripcion: string | null
  orden_compra_uuid: string | null
  creado_en: string
}

export interface GastosDelDiaCable {
  dia: string
  gastos: GastoCable[]
  total: SaldoPorMedioCable
  del_puesto: string
  del_hogar: string
}

// ------------------------------------------------------------------ análisis (Fase 7)

export type PeriodoAnalisis = 'semana' | 'mes' | 'mes_pasado'

export interface DiaDelPeriodoCable {
  dia: string
  vendido: string
  gastado: string
}

export interface GananciaPorProductoCable {
  nombre: string
  vendido: string
  ganancia_estimada: string
}

export interface AnalisisCable {
  periodo: PeriodoAnalisis
  desde: string
  hasta: string
  vendido: string
  ventas: number
  pagado_a_proveedores: string
  gastos_del_puesto: string
  gastos_de_la_casa: string
  resultado_del_negocio: string
  libre: string
  fiados_por_cobrar: string
  por_dia: DiaDelPeriodoCable[]
  mejores_productos: GananciaPorProductoCable[]
  no_disponibles: string[]
}

export const CAMPOS_DEL_CONTRATO = {
  AnalisisDelPeriodo: camposDe<AnalisisCable>()([
    'periodo',
    'desde',
    'hasta',
    'vendido',
    'ventas',
    'pagado_a_proveedores',
    'gastos_del_puesto',
    'gastos_de_la_casa',
    'resultado_del_negocio',
    'libre',
    'fiados_por_cobrar',
    'por_dia',
    'mejores_productos',
    'no_disponibles',
  ]),
  DiaDelPeriodo: camposDe<DiaDelPeriodoCable>()(['dia', 'vendido', 'gastado']),
  GananciaPorProducto: camposDe<GananciaPorProductoCable>()(['nombre', 'vendido', 'ganancia_estimada']),
  SaldoPorMedio: camposDe<SaldoPorMedioCable>()(['efectivo', 'yape_plin']),
  TotalesPorMedio: camposDe<SaldoPorMedioCable>()(['efectivo', 'yape_plin']),
  CajaDelDia: camposDe<CajaDelDiaCable>()([
    'dia',
    'abierta',
    'inicial',
    'ingresos',
    'egresos',
    'en_caja',
    'no_disponibles',
  ]),
  GastoSalida: camposDe<GastoCable>()([
    'uuid',
    'monto',
    'medio',
    'ambito',
    'categoria',
    'descripcion',
    'orden_compra_uuid',
    'creado_en',
  ]),
  GastosDelDia: camposDe<GastosDelDiaCable>()(['dia', 'gastos', 'total', 'del_puesto', 'del_hogar']),
  IngresoSalida: camposDe<IngresoCable>()(['token', 'proyecto', 'nombre_proyecto', 'es_real']),
  CuentaVisible: camposDe<CuentaVisibleCable>()(['nombre_usuario', 'nombre_proyecto', 'es_real']),
  ResumenDashboard: camposDe<ResumenDashboardCable>()([
    'ventas_hoy',
    'ventas_cerradas',
    'proyeccion_manana',
    'motivo_proyeccion',
    'ordenes_activas',
    'fiados_por_cobrar',
    'clientes_con_fiado',
    'ventas_rapidas_pendientes',
    'pedidos_por_llegar',
    'productos_por_vencer',
    'secciones_no_disponibles',
  ]),
  OrdenActivaResumen: camposDe<OrdenActivaResumenCable>()([
    'uuid',
    'nombre',
    'tipo',
    'monto',
    'deuda_cliente',
  ]),
  PedidoPorLlegar: camposDe<PedidoPorLlegarCable>()(['uuid', 'proveedor', 'fecha_estimada', 'monto']),
  VentaSalida: camposDe<VentaCable>()([
    'uuid',
    'tipo',
    'cliente_uuid',
    'cliente_nombre',
    'nombre_orden',
    'estado',
    'monto_total',
    'metodo_pago',
    'abierta_en',
    'cerrada_en',
    'items',
    'deuda_cliente',
  ]),
  ItemVentaSalida: camposDe<ItemVentaCable>()([
    'uuid',
    'nombre_producto',
    'cantidad',
    'monto',
    'producto_uuid',
    'cantidad_num',
  ]),
  ResultadoVenta: camposDe<ResultadoVentaCable>()(['venta', 'avisos']),
  ProveedorSalida: camposDe<ProveedorCable>()([
    'uuid',
    'nombre',
    'empresa',
    'ruc',
    'telefono',
    'categoria',
    'creado_en',
  ]),
  ItemOrdenCompraSalida: camposDe<ItemOrdenCompraCable>()([
    'uuid',
    'nombre_producto',
    'cantidad',
    'monto',
    'estado_recepcion',
    'producto_sustituto',
    'monto_sustituto',
  ]),
  OrdenCompraSalida: camposDe<OrdenCompraCable>()([
    'uuid',
    'proveedor_uuid',
    'proveedor',
    'proveedor_telefono',
    'estado',
    'fecha_estimada_llegada',
    'monto_total',
    'monto_real',
    'notas',
    'items',
  ]),
  ResultadoOrden: camposDe<ResultadoOrdenCable>()(['orden', 'avisos']),
  EstadoAsistente: camposDe<EstadoAsistenteCable>()(['listo', 'puede_guardar_llave', 'llave_guardada']),
  ProductoConEstado: camposDe<ProductoCable>()([
    'uuid',
    'nombre',
    'unidad',
    'precio_venta',
    'stock_actual',
    'stock_minimo',
    'codigo_barras',
    'tiene_vencimiento',
    'costo_ultimo',
    'vence_el',
    'bajo_minimo',
    'descuadre',
    'vence_pronto',
    'vencido',
  ]),
  MovimientoSalida: camposDe<MovimientoCable>()(['delta', 'motivo', 'origen_tipo', 'nota', 'creado_en']),
  ProductoFrecuente: camposDe<ProductoFrecuenteCable>()(['nombre_producto', 'cantidad', 'monto', 'veces']),
  ClienteSalida: camposDe<ClienteCable>()(['uuid', 'nombre', 'telefono', 'limite_credito', 'creado_en']),
  ClienteConDeuda: camposDe<ClienteConDeudaCable>()([
    'uuid',
    'nombre',
    'telefono',
    'limite_credito',
    'creado_en',
    'deuda',
  ]),
  RespuestaSalida: camposDe<RespuestaAsistenteCable>()([
    'respuesta',
    'acciones',
    'borrador',
    'formulario',
    'recordado',
    'id_respuesta',
    'modelo',
  ]),
  RecuerdoSalida: camposDe<RecuerdoCable>()(['uuid', 'texto', 'creado_en']),
  BorradorVenta: camposDe<BorradorVentaCable>()(['items', 'para']),
  ItemBorrador: camposDe<ItemBorradorCable>()(['nombre', 'cantidad', 'precio']),
  FormularioLlenado: camposDe<FormularioLlenadoCable>()([
    'tipo',
    'cliente',
    'producto',
    'monto',
    'cantidad',
    'medio',
    'ambito',
    'categoria',
    'nota',
  ]),
  AccionSugerida: camposDe<AccionSugeridaCable>()(['tipo', 'pantalla', 'etiqueta', 'automatica', 'apartado']),
  AbonoSalida: camposDe<AbonoCable>()([
    'uuid',
    'cliente_uuid',
    'monto',
    'metodo_pago',
    'creado_en',
    'deuda_restante',
    'avisos',
  ]),
} as const
