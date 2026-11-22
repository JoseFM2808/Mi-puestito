import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { SinConexion, pedir } from '../../api/cliente'
import {
  aCentimos,
  formatearCentimos,
  leerMontoEscrito,
  type EstadoRecepcion,
  type ItemPedidoCable,
  type OrdenCompraCable,
  type PedidoLlenadoCable,
  type ProductoFrecuenteCable,
  type ProveedorCable,
} from '../../api/contrato'
import type { OrigenPedido } from '../../stores/borradorAsistente'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Monto, Nota, Tarjeta, TituloPagina, TituloSeccion } from '../../ui/componentes'
import { aMilesimas, formatearCantidad, useInventario } from '../inventario/almacen'
import { diaPeruano, useCompras, type EntradaRecepcion, type ItemNuevo } from './almacen'
import estilos from './Compras.module.css'

// ---------------------------------------------------------------- proveedor

/**
 * Alta de proveedor. Pensada para pasarle la tablet: el proveedor llena sus propios
 * datos, y solo el nombre es obligatorio. El RUC se escribe, no se consulta en SUNAT.
 */
function RegistroProveedor({
  alTerminar,
  alCancelar,
  nombreInicial,
}: {
  alTerminar: (proveedor: ProveedorCable) => void
  alCancelar: () => void
  nombreInicial: string
}) {
  const proveedores = useCompras((estado) => estado.proveedores)
  const registrarProveedor = useCompras((estado) => estado.registrarProveedor)
  const [nombre, setNombre] = useState(nombreInicial)
  const [empresa, setEmpresa] = useState('')
  const [ruc, setRuc] = useState('')
  const [telefono, setTelefono] = useState('')
  const [categoria, setCategoria] = useState('')
  const [error, setError] = useState<string | null>(null)

  const guardar = async (evento: FormEvent) => {
    evento.preventDefault()
    if (!nombre.trim()) return setError('Escribe el nombre del proveedor.')
    const rucLimpio = ruc.trim()
    if (rucLimpio && !/^\d{11}$/.test(rucLimpio)) return setError('El RUC tiene 11 números.')
    const conRuc = rucLimpio && proveedores.find((p) => p.ruc === rucLimpio)
    if (conRuc) return setError(`Ese RUC ya está registrado a nombre de ${conRuc.nombre}.`)
    alTerminar(
      await registrarProveedor({
        nombre: nombre.trim(),
        empresa: empresa.trim(),
        ruc: rucLimpio,
        telefono: telefono.trim(),
        categoria: categoria.trim(),
      }),
    )
  }

  return (
    <form
      className={estilos.formulario}
      onSubmit={(evento) => void guardar(evento)}
      data-ai-id="compras.proveedor"
    >
      <TituloSeccion>Datos del proveedor</TituloSeccion>
      <Nota>Puedes pasarle la tablet para que los llene. Solo el nombre es obligatorio.</Nota>
      {error && <Aviso tipo="error">{error}</Aviso>}
      <div className={estilos.filaCampos}>
        <Campo
          id="prov-nombre"
          aiId="compras.proveedor-nombre"
          etiqueta="Nombre"
          valor={nombre}
          alCambiar={setNombre}
        />
        <Campo
          id="prov-empresa"
          aiId="compras.proveedor-empresa"
          etiqueta="Empresa"
          valor={empresa}
          alCambiar={setEmpresa}
        />
        <Campo
          id="prov-ruc"
          aiId="compras.proveedor-ruc"
          etiqueta="RUC"
          valor={ruc}
          alCambiar={setRuc}
          inputMode="numeric"
          maxLength={11}
        />
        <Campo
          id="prov-telefono"
          aiId="compras.proveedor-telefono"
          etiqueta="Teléfono"
          valor={telefono}
          alCambiar={setTelefono}
          inputMode="tel"
          maxLength={20}
        />
        <Campo
          id="prov-categoria"
          aiId="compras.proveedor-categoria"
          etiqueta="Qué vende"
          valor={categoria}
          alCambiar={setCategoria}
          maxLength={80}
        />
      </div>
      <div className={estilos.acciones}>
        <Boton aiId="compras.proveedor-guardar" tipo="submit">
          Guardar proveedor
        </Boton>
        <Boton aiId="compras.proveedor-cancelar" variante="discreto" onClick={alCancelar}>
          Cancelar
        </Boton>
      </div>
    </form>
  )
}

function ElegirProveedor({
  alElegir,
  busquedaInicial = '',
}: {
  alElegir: (proveedor: ProveedorCable) => void
  busquedaInicial?: string
}) {
  const proveedores = useCompras((estado) => estado.proveedores)
  const [busqueda, setBusqueda] = useState(busquedaInicial)
  const [registrando, setRegistrando] = useState(false)

  const texto = busqueda.trim().toLowerCase()
  const visibles = proveedores.filter(
    (p) =>
      p.nombre.toLowerCase().includes(texto) ||
      (p.empresa ?? '').toLowerCase().includes(texto) ||
      (p.ruc ?? '').includes(texto),
  )

  if (registrando) {
    return (
      <RegistroProveedor
        nombreInicial={busqueda.trim()}
        alTerminar={alElegir}
        alCancelar={() => setRegistrando(false)}
      />
    )
  }
  return (
    <>
      <TituloSeccion>¿A qué proveedor le pides?</TituloSeccion>
      <Campo
        id="buscar-proveedor"
        aiId="compras.buscar-proveedor"
        etiqueta="Buscar por nombre, empresa o RUC"
        valor={busqueda}
        alCambiar={setBusqueda}
      />
      <div className={estilos.opciones}>
        {visibles.map((proveedor) => (
          <Boton
            key={proveedor.uuid}
            aiId={`compras.elegir-${proveedor.uuid}`}
            variante="secundario"
            onClick={() => alElegir(proveedor)}
          >
            {proveedor.empresa ? `${proveedor.nombre} (${proveedor.empresa})` : proveedor.nombre}
          </Boton>
        ))}
      </div>
      {visibles.length === 0 && <Nota>No encontramos a ese proveedor. Puedes registrarlo.</Nota>}
      <Boton aiId="compras.registrar-proveedor" variante="discreto" onClick={() => setRegistrando(true)}>
        Registrar proveedor nuevo
      </Boton>
    </>
  )
}

// ---------------------------------------------------------------- pedido

const OPCIONES_LLEGADA = [
  { dias: 0, nombre: 'Hoy' },
  { dias: 1, nombre: 'Mañana' },
  { dias: 2, nombre: 'Pasado mañana' },
]

/** El proveedor guardado que el operador nombró, por nombre o empresa, sin importar mayúsculas */
export function buscarProveedor(proveedores: ProveedorCable[], nombre: string | null): ProveedorCable | null {
  const buscado = (nombre ?? '').trim().toLowerCase()
  if (!buscado) return null
  return (
    proveedores.find(
      (p) => p.nombre.toLowerCase() === buscado || (p.empresa ?? '').toLowerCase() === buscado,
    ) ?? null
  )
}

/** Los productos que llenó el Asistente: con monto van al pedido; sin monto esperan al operador */
export function repartirLlenado(llenado?: PedidoLlenadoCable): {
  listos: ItemNuevo[]
  sinMonto: ItemPedidoCable[]
} {
  const listos: ItemNuevo[] = []
  const sinMonto: ItemPedidoCable[] = []
  for (const item of llenado?.items ?? []) {
    const centimos = item.monto ? aCentimos(item.monto) : 0
    if (centimos > 0) listos.push({ nombre: item.producto, cantidad: item.cantidad ?? '', centimos })
    else sinMonto.push(item)
  }
  return { listos, sinMonto }
}

/** Lo que se está acabando según Inventario y aún no está en el pedido (comparando nombres) */
export function porAcabarse<T extends { nombre: string; bajo_minimo: boolean }>(
  productos: T[],
  yaEnElPedido: string[],
): T[] {
  const ya = new Set(yaEnElPedido.map((n) => n.trim().toLowerCase()))
  return productos.filter((p) => p.bajo_minimo && !ya.has(p.nombre.trim().toLowerCase()))
}

export function NuevoPedido({
  alTerminar,
  llenado,
  origen = 'asistente',
}: {
  alTerminar: () => void
  /** Lo que llenó el Asistente (o Inventario); el operador lo revisa y lo guarda */
  llenado?: PedidoLlenadoCable
  origen?: OrigenPedido
}) {
  const crearPedido = useCompras((estado) => estado.crearPedido)
  const proveedores = useCompras((estado) => estado.proveedores)
  // Inventario es opcional: si no está o falla, el pedido se arma igual, sin "se te está acabando"
  const proyecto = useSesion((estado) => estado.proyecto)
  const productos = useInventario((estado) => estado.productos)
  const proyectoInventario = useInventario((estado) => estado.proyecto)
  const iniciarInventario = useInventario((estado) => estado.iniciar)
  const [inicial] = useState(() => repartirLlenado(llenado))
  const [proveedor, setProveedor] = useState<ProveedorCable | null>(() =>
    buscarProveedor(proveedores, llenado?.proveedor ?? null),
  )
  const [frecuentes, setFrecuentes] = useState<ProductoFrecuenteCable[]>([])
  const [items, setItems] = useState<ItemNuevo[]>(inicial.listos)
  const [sinMonto, setSinMonto] = useState<ItemPedidoCable[]>(inicial.sinMonto)
  const [nombre, setNombre] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [monto, setMonto] = useState('')
  const [fecha, setFecha] = useState(diaPeruano(1))
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (proyecto && proyectoInventario !== proyecto) void iniciarInventario(proyecto).catch(() => {})
  }, [proyecto, proyectoInventario, iniciarInventario])

  // Los proveedores pueden terminar de leerse después de abrir el pedido
  useEffect(() => {
    if (!proveedor && llenado?.proveedor) {
      const encontrado = buscarProveedor(proveedores, llenado.proveedor)
      if (encontrado) setProveedor(encontrado)
    }
    // Solo cuando cambia la lista: si el operador elige otro, no se vuelve a imponer
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proveedores])

  const completar = (indice: number) => {
    const item = sinMonto[indice]
    setNombre(item.producto)
    setCantidad(item.cantidad ?? '')
    setMonto('')
    setSinMonto(sinMonto.filter((_, i) => i !== indice))
    document.getElementById('item-monto')?.focus()
  }

  useEffect(() => {
    if (!proveedor) return
    let vigente = true
    pedir<ProductoFrecuenteCable[]>('GET', `/api/compras/proveedores/${proveedor.uuid}/frecuentes`)
      .then((lista) => {
        if (vigente) setFrecuentes(lista)
      })
      .catch((fallo: unknown) => {
        // Sin red, o un proveedor aún sin enviar: el pedido se arma igual, sin sugerencias
        if (!(fallo instanceof SinConexion)) setFrecuentes([])
      })
    return () => {
      vigente = false
    }
  }, [proveedor])

  const total = items.reduce((suma, item) => suma + item.centimos, 0)
  const acabandose = porAcabarse(productos, [
    ...items.map((i) => i.nombre),
    ...sinMonto.map((i) => i.producto),
    nombre,
  ])

  /** Lleva un producto que se acaba al formulario; si se le suele pedir a este proveedor, con lo de siempre */
  const pedirLoQueSeAcaba = (producto: (typeof productos)[number]) => {
    const deSiempre = frecuentes.find(
      (f) => f.nombre_producto.toLowerCase() === producto.nombre.toLowerCase(),
    )
    setNombre(producto.nombre)
    setCantidad(deSiempre?.cantidad ?? '')
    setMonto(deSiempre?.monto ?? '')
    document.getElementById(deSiempre ? 'item-monto' : 'item-cantidad')?.focus()
  }
  const sugeridos = frecuentes.filter(
    (f) => !items.some((item) => item.nombre.toLowerCase() === f.nombre_producto.toLowerCase()),
  )

  const agregar = (evento: FormEvent) => {
    evento.preventDefault()
    if (!nombre.trim()) return setError('Escribe qué producto pides.')
    const centimos = leerMontoEscrito(monto)
    if (!centimos) return setError('Escribe cuánto cuesta en total, por ejemplo 180')
    setItems([...items, { nombre: nombre.trim(), cantidad: cantidad.trim(), centimos }])
    setNombre('')
    setCantidad('')
    setMonto('')
    setError(null)
  }

  const guardar = (borrador: boolean) => {
    if (!proveedor || items.length === 0) return
    void crearPedido({ proveedor, items, fechaEstimada: fecha || undefined, borrador })
    alTerminar()
  }

  return (
    <main className={estilos.pantalla} data-ai-id="compras.nuevo">
      <TituloPagina>Nuevo pedido</TituloPagina>
      {llenado && (
        <Aviso tipo="info" aiId="compras.llenado-asistente">
          {origen === 'inventario'
            ? 'Con lo que se te está acabando en Inventario. Elige el proveedor, escribe cuánto cuesta cada cosa y toca «Guardar pedido».'
            : 'Lo llenó el Asistente: revísalo y toca «Guardar pedido». Aún no se guardó nada.'}
        </Aviso>
      )}
      {!proveedor ? (
        <>
          <ElegirProveedor alElegir={setProveedor} busquedaInicial={llenado?.proveedor ?? ''} />
          <Boton aiId="compras.nuevo-cancelar" variante="discreto" onClick={alTerminar}>
            Volver a Compras
          </Boton>
        </>
      ) : (
        <>
          <div className={estilos.fila}>
            <div className={estilos.nombre}>{proveedor.nombre}</div>
            <Boton aiId="compras.cambiar-proveedor" variante="discreto" onClick={() => setProveedor(null)}>
              Cambiar proveedor
            </Boton>
          </div>

          {sugeridos.length > 0 && (
            <>
              <TituloSeccion>Lo que le sueles pedir</TituloSeccion>
              <div className={estilos.opciones}>
                {sugeridos.map((producto, indice) => (
                  <Boton
                    key={producto.nombre_producto}
                    aiId={`compras.sugerido-${indice}`}
                    variante="secundario"
                    onClick={() => {
                      setNombre(producto.nombre_producto)
                      setCantidad(producto.cantidad ?? '')
                      setMonto(producto.monto)
                    }}
                  >
                    {`${producto.nombre_producto}${producto.cantidad ? ` · ${producto.cantidad}` : ''}`}
                  </Boton>
                ))}
              </div>
            </>
          )}

          {sinMonto.length > 0 && (
            <section data-ai-id="compras.falta-monto">
              <TituloSeccion>Falta cuánto cuesta</TituloSeccion>
              <Nota>Toca cada uno, escribe el monto y agrégalo al pedido.</Nota>
              <div className={estilos.opciones}>
                {sinMonto.map((item, indice) => (
                  <Boton
                    key={`${indice}-${item.producto}`}
                    aiId={`compras.completar-${indice}`}
                    variante="secundario"
                    onClick={() => completar(indice)}
                  >
                    {`${item.producto}${item.cantidad ? ` · ${item.cantidad}` : ''}: escribir el monto`}
                  </Boton>
                ))}
              </div>
            </section>
          )}

          {acabandose.length > 0 && (
            <section data-ai-id="compras.se-acaba">
              <TituloSeccion>Se te está acabando</TituloSeccion>
              <div className={estilos.opciones}>
                {acabandose.map((producto) => (
                  <Boton
                    key={producto.uuid}
                    aiId={`compras.se-acaba-${producto.uuid}`}
                    variante="secundario"
                    onClick={() => pedirLoQueSeAcaba(producto)}
                  >
                    {`${producto.nombre} (quedan ${formatearCantidad(aMilesimas(producto.stock_actual), producto.unidad)})`}
                  </Boton>
                ))}
              </div>
            </section>
          )}

          <form className={estilos.formulario} onSubmit={agregar}>
            <TituloSeccion>Agregar producto</TituloSeccion>
            {error && <Aviso tipo="error">{error}</Aviso>}
            <div className={estilos.filaCampos}>
              <Campo
                id="item-nombre"
                aiId="compras.item-nombre"
                etiqueta="Producto"
                valor={nombre}
                alCambiar={setNombre}
              />
              <Campo
                id="item-cantidad"
                aiId="compras.item-cantidad"
                etiqueta="Cantidad"
                ayuda="Por ejemplo: 2 packs"
                valor={cantidad}
                alCambiar={setCantidad}
                maxLength={60}
              />
              <Campo
                id="item-monto"
                aiId="compras.item-monto"
                etiqueta="Monto total en soles"
                valor={monto}
                alCambiar={setMonto}
                inputMode="decimal"
              />
            </div>
            <Boton aiId="compras.item-agregar" variante="secundario" tipo="submit">
              Agregar al pedido
            </Boton>
          </form>

          {items.length > 0 && (
            <Tarjeta aiId="compras.resumen-pedido" className={estilos.tarjeta}>
              {items.map((item, indice) => (
                <div key={`${indice}-${item.nombre}`} className={estilos.fila}>
                  <span>
                    {item.nombre}
                    {item.cantidad ? ` · ${item.cantidad}` : ''}
                  </span>
                  <span className={estilos.filaDerecha}>
                    <Monto centimos={item.centimos} />
                    <Boton
                      aiId={`compras.item-quitar-${indice}`}
                      variante="discreto"
                      onClick={() => setItems(items.filter((_, i) => i !== indice))}
                    >
                      Quitar
                    </Boton>
                  </span>
                </div>
              ))}
              <div className={estilos.fila}>
                <span className={estilos.nombre}>Total</span>
                <Monto centimos={total} tamano="orden" tono="pendiente" />
              </div>
            </Tarjeta>
          )}

          <TituloSeccion>¿Cuándo llega?</TituloSeccion>
          <div className={estilos.opciones}>
            {OPCIONES_LLEGADA.map(({ dias, nombre: nombreDia }) => (
              <Boton
                key={dias}
                aiId={`compras.llegada-${dias}`}
                variante="secundario"
                presionado={fecha === diaPeruano(dias)}
                onClick={() => setFecha(diaPeruano(dias))}
              >
                {nombreDia}
              </Boton>
            ))}
          </div>
          <Campo
            id="fecha-llegada"
            aiId="compras.llegada-fecha"
            etiqueta="U otro día"
            type="date"
            valor={fecha}
            alCambiar={setFecha}
          />

          <div className={estilos.acciones}>
            <Boton
              aiId="compras.pedido-guardar"
              deshabilitado={items.length === 0}
              onClick={() => guardar(false)}
            >
              Guardar pedido
            </Boton>
            <Boton
              aiId="compras.pedido-borrador"
              variante="secundario"
              deshabilitado={items.length === 0}
              onClick={() => guardar(true)}
            >
              Guardar como borrador
            </Boton>
            <Boton aiId="compras.pedido-cancelar" variante="discreto" onClick={alTerminar}>
              Cancelar
            </Boton>
          </div>
        </>
      )}
    </main>
  )
}

// ---------------------------------------------------------------- recepción

interface ProductoInventario {
  nombre: string
  unidad: string
}

interface Marca {
  estado: EstadoRecepcion
  sustituto: string
  montoSustituto: string
  cantidadStock: string
}

const MARCA_VACIA: Marca = { estado: 'pendiente', sustituto: '', montoSustituto: '', cantidadStock: '' }

const UNIDADES: Record<string, string> = { unidad: 'unidades', kg: 'kg', litro: 'litros' }

/** Checklist de llegada: recibido, no llegó o cambió. El monto a pagar se recalcula a la vista. */
export function ChecklistRecepcion({
  orden,
  alTerminar,
}: {
  orden: OrdenCompraCable
  alTerminar: () => void
}) {
  const recibir = useCompras((estado) => estado.recibir)
  const [marcas, setMarcas] = useState<Record<string, Marca>>({})
  const [enInventario, setEnInventario] = useState<ProductoInventario[]>([])
  const [error, setError] = useState<string | null>(null)

  // Lo ya confirmado en una llegada anterior no se vuelve a preguntar
  const porConfirmar = orden.items.filter((item) => item.estado_recepcion === 'pendiente')

  useEffect(() => {
    // Inventario es opcional: sin él (o sin red) simplemente no se pregunta la cantidad
    pedir<ProductoInventario[]>('GET', '/api/inventario/productos')
      .then(setEnInventario)
      .catch(() => setEnInventario([]))
  }, [])

  const marcaDe = (uuid: string) => marcas[uuid] ?? MARCA_VACIA
  const cambiar = (uuid: string, cambio: Partial<Marca>) =>
    setMarcas({ ...marcas, [uuid]: { ...marcaDe(uuid), ...cambio } })
  const productoDe = (nombre: string) =>
    enInventario.find((p) => p.nombre.toLowerCase() === nombre.trim().toLowerCase())

  const montoReal = useMemo(() => {
    let total = 0
    for (const item of orden.items) {
      if (item.estado_recepcion === 'recibido') total += aCentimos(item.monto)
      else if (item.estado_recepcion === 'cambiado') total += aCentimos(item.monto_sustituto ?? '0')
      else if (marcas[item.uuid]?.estado === 'recibido') total += aCentimos(item.monto)
      else if (marcas[item.uuid]?.estado === 'cambiado') {
        total += leerMontoEscrito(marcas[item.uuid].montoSustituto) ?? 0
      }
    }
    return total
  }, [orden.items, marcas])

  const confirmar = () => {
    const entradas: EntradaRecepcion[] = []
    for (const item of porConfirmar) {
      const marca = marcaDe(item.uuid)
      const entrada: EntradaRecepcion = { itemUuid: item.uuid, estado: marca.estado }
      if (marca.estado === 'cambiado') {
        const montoSustituto = leerMontoEscrito(marca.montoSustituto)
        if (!marca.sustituto.trim() || montoSustituto === null) {
          return setError(`Falta qué llegó en lugar de ${item.nombre_producto} y cuánto cuesta.`)
        }
        entrada.productoSustituto = marca.sustituto.trim()
        entrada.montoSustitutoCentimos = montoSustituto
      }
      if (marca.estado === 'recibido' || marca.estado === 'cambiado') {
        if (marca.cantidadStock.trim()) {
          if (!/^\d+([.,]\d{1,3})?$/.test(marca.cantidadStock.trim())) {
            return setError(`La cantidad de ${item.nombre_producto} debe ser un número.`)
          }
          entrada.cantidadStock = marca.cantidadStock.trim().replace(',', '.')
        }
      }
      entradas.push(entrada)
    }
    if (entradas.every((e) => e.estado === 'pendiente')) {
      return setError('Marca al menos un producto: llegó, no llegó o cambió.')
    }
    void recibir(orden.uuid, entradas)
    alTerminar()
  }

  return (
    <main className={estilos.pantalla} data-ai-id="compras.recepcion">
      <TituloPagina>{`Llegó el pedido de ${orden.proveedor}`}</TituloPagina>
      <Nota>Revisa cada producto. Lo que marques como pendiente queda para cuando llegue.</Nota>
      {error && <Aviso tipo="error">{error}</Aviso>}

      {porConfirmar.map((item) => {
        const marca = marcaDe(item.uuid)
        const nombreFinal = marca.estado === 'cambiado' ? marca.sustituto : item.nombre_producto
        const enStock = productoDe(nombreFinal)
        return (
          <Tarjeta key={item.uuid} aiId={`compras.check-${item.uuid}`} className={estilos.tarjeta}>
            <div className={estilos.fila}>
              <div>
                <div className={estilos.nombre}>{item.nombre_producto}</div>
                {item.cantidad && <Nota>{item.cantidad}</Nota>}
              </div>
              <Monto centimos={aCentimos(item.monto)} />
            </div>
            <div className={estilos.opciones}>
              {(
                [
                  ['recibido', 'Llegó'],
                  ['no_recibido', 'No llegó'],
                  ['cambiado', 'Cambió'],
                ] as const
              ).map(([estado, texto]) => (
                <Boton
                  key={estado}
                  aiId={`compras.check-${estado}-${item.uuid}`}
                  variante="secundario"
                  presionado={marca.estado === estado}
                  onClick={() => cambiar(item.uuid, { estado })}
                >
                  {texto}
                </Boton>
              ))}
            </div>

            {marca.estado === 'no_recibido' && (
              <div className={estilos.bloque}>
                <Nota>Se saca del pedido y no se paga.</Nota>
                <div className={estilos.opciones}>
                  {orden.proveedor_telefono && (
                    <a
                      className={estilos.enlaceLlamar}
                      href={`tel:${orden.proveedor_telefono}`}
                      data-ai-id={`compras.llamar-${item.uuid}`}
                    >
                      {`Llamar a ${orden.proveedor}`}
                    </a>
                  )}
                  <Boton
                    aiId={`compras.check-pendiente-${item.uuid}`}
                    variante="discreto"
                    onClick={() => cambiar(item.uuid, { estado: 'pendiente' })}
                  >
                    Mejor dejarlo pendiente
                  </Boton>
                </div>
              </div>
            )}

            {marca.estado === 'cambiado' && (
              <div className={estilos.filaCampos}>
                <Campo
                  id={`sustituto-${item.uuid}`}
                  aiId={`compras.sustituto-${item.uuid}`}
                  etiqueta="¿Qué llegó en su lugar?"
                  valor={marca.sustituto}
                  alCambiar={(valor) => cambiar(item.uuid, { sustituto: valor })}
                />
                <Campo
                  id={`monto-sustituto-${item.uuid}`}
                  aiId={`compras.monto-sustituto-${item.uuid}`}
                  etiqueta="¿Cuánto cuesta?"
                  valor={marca.montoSustituto}
                  alCambiar={(valor) => cambiar(item.uuid, { montoSustituto: valor })}
                  inputMode="decimal"
                />
              </div>
            )}

            {(marca.estado === 'recibido' || marca.estado === 'cambiado') && enStock && (
              <Campo
                id={`stock-${item.uuid}`}
                aiId={`compras.stock-${item.uuid}`}
                etiqueta={`¿Cuántos ${UNIDADES[enStock.unidad] ?? ''} entran al stock de ${enStock.nombre}?`}
                ayuda="Si lo dejas vacío, el stock no cambia."
                valor={marca.cantidadStock}
                alCambiar={(valor) => cambiar(item.uuid, { cantidadStock: valor })}
                inputMode="decimal"
              />
            )}
          </Tarjeta>
        )
      })}

      <Tarjeta aiId="compras.monto-real" className={estilos.tarjeta}>
        <div className={estilos.fila}>
          <span className={estilos.nombre}>A pagar por lo que llegó</span>
          <Monto centimos={montoReal} tamano="orden" tono="deuda" />
        </div>
        <Nota>Se había pedido por {formatearCentimos(aCentimos(orden.monto_total))}.</Nota>
      </Tarjeta>

      <div className={estilos.acciones}>
        <Boton aiId="compras.recepcion-confirmar" onClick={confirmar}>
          Confirmar lo que llegó
        </Boton>
        <Boton aiId="compras.recepcion-cancelar" variante="discreto" onClick={alTerminar}>
          Volver sin guardar
        </Boton>
      </div>
    </main>
  )
}
