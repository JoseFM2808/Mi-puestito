import { useEffect, useState } from 'react'
import {
  aCentimos,
  aSoles,
  leerMontoEscrito,
  type ClienteCable,
  type MetodoPago,
  type ProductoCable,
} from '../../api/contrato'
import { useSesion } from '../../stores/sesion'
import { Boton, Campo, Nota, Tarjeta } from '../../ui/componentes'
import {
  aMilesimas,
  formatearCantidad,
  leerCantidadEscrita,
  montoPorCantidad,
  useInventario,
} from '../inventario/almacen'
import { useVentas } from './almacen'
import estilos from './Ventas.module.css'

/**
 * Formularios del módulo Ventas. Cada uno valida en palabras simples antes
 * de enviar y deja el foco donde el operador lo necesita.
 */

const MAX_SUGERENCIAS = 4

/**
 * Producto vendido. Si coincide con uno del inventario, se puede elegir: entonces la
 * cantidad va en su unidad, el monto se sugiere con su precio y el servidor descuenta
 * el stock (ADR-031). Sin elegir, se vende con texto libre, como siempre: el inventario
 * es opcional.
 */
export function FormularioProducto({
  prefijo,
  alAgregar,
}: {
  /** Distingue los ids cuando hay más de un formulario en pantalla */
  prefijo: string
  alAgregar: (datos: {
    nombre: string
    cantidad: string
    centimos: number
    producto?: { uuid: string; milesimas: number }
  }) => void
}) {
  const proyecto = useSesion((estado) => estado.proyecto)
  const productos = useInventario((estado) => estado.productos)
  const proyectoInventario = useInventario((estado) => estado.proyecto)
  const iniciarInventario = useInventario((estado) => estado.iniciar)
  const [nombre, setNombre] = useState('')
  const [elegido, setElegido] = useState<ProductoCable | null>(null)
  const [cantidad, setCantidad] = useState('')
  const [monto, setMonto] = useState('')
  const [montoEscrito, setMontoEscrito] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Sin red se usa lo guardado en el dispositivo; si falla, se vende con texto libre
    if (proyecto && proyectoInventario !== proyecto) void iniciarInventario(proyecto).catch(() => {})
  }, [proyecto, proyectoInventario, iniciarInventario])

  const texto = nombre.trim().toLowerCase()
  const sugerencias =
    elegido || !texto
      ? []
      : productos.filter((p) => p.nombre.toLowerCase().includes(texto)).slice(0, MAX_SUGERENCIAS)

  const cambiarCantidad = (valor: string) => {
    setCantidad(valor)
    if (!elegido?.precio_venta || montoEscrito) return
    const milesimas = leerCantidadEscrita(valor)
    setMonto(milesimas ? aSoles(montoPorCantidad(aCentimos(elegido.precio_venta), milesimas)) : '')
  }

  const elegir = (producto: ProductoCable) => {
    setElegido(producto)
    setNombre(producto.nombre)
    setCantidad('')
    setMonto('')
    setMontoEscrito(false)
    setError(null)
  }

  const soltar = () => {
    setElegido(null)
    setCantidad('')
    setMonto('')
    setMontoEscrito(false)
  }

  const enviar = (evento: React.FormEvent) => {
    evento.preventDefault()
    const centimos = leerMontoEscrito(monto)
    if (!nombre.trim()) return setError('Escribe qué producto vendiste.')
    let producto: { uuid: string; milesimas: number } | undefined
    if (elegido) {
      const milesimas = leerCantidadEscrita(cantidad)
      if (!milesimas)
        return setError(`Escribe cuántos ${unidadEnPlural(elegido.unidad)} vendiste, por ejemplo 2`)
      producto = { uuid: elegido.uuid, milesimas }
    }
    if (centimos === null) return setError('Escribe el monto en soles, por ejemplo 12.50')
    alAgregar({
      nombre: nombre.trim(),
      cantidad: elegido && producto ? formatearCantidad(producto.milesimas, elegido.unidad) : cantidad.trim(),
      centimos,
      producto,
    })
    setNombre('')
    soltar()
    setError(null)
  }

  return (
    <form className={estilos.formulario} onSubmit={enviar} noValidate>
      {elegido ? (
        <div className={estilos.productoElegido} data-ai-id={`${prefijo}.producto-elegido`}>
          <span>
            <strong>{elegido.nombre}</strong>
            {` · quedan ${formatearCantidad(aMilesimas(elegido.stock_actual), elegido.unidad)}`}
          </span>
          <Boton aiId={`${prefijo}.soltar-producto`} variante="discreto" onClick={soltar}>
            Escribir otro producto
          </Boton>
        </div>
      ) : (
        <Campo
          id={`${prefijo}-producto`}
          aiId={`${prefijo}.producto`}
          etiqueta="Producto"
          valor={nombre}
          alCambiar={setNombre}
          autoComplete="off"
          maxLength={120}
        />
      )}
      {sugerencias.length > 0 && (
        <div className={estilos.sugerencias} data-ai-id={`${prefijo}.sugerencias`}>
          {sugerencias.map((producto, indice) => (
            <Boton
              key={producto.uuid}
              aiId={`${prefijo}.sugerido-${indice}`}
              variante="secundario"
              onClick={() => elegir(producto)}
            >
              {`${producto.nombre} (quedan ${formatearCantidad(aMilesimas(producto.stock_actual), producto.unidad)})`}
            </Boton>
          ))}
        </div>
      )}
      <div className={estilos.filaCampos}>
        <Campo
          id={`${prefijo}-cantidad`}
          aiId={`${prefijo}.cantidad`}
          etiqueta={elegido ? `¿Cuántos ${unidadEnPlural(elegido.unidad)}?` : 'Cantidad (opcional)'}
          ayuda={elegido ? 'Se descuenta del inventario' : 'Por ejemplo: 2 kg'}
          valor={cantidad}
          alCambiar={cambiarCantidad}
          autoComplete="off"
          inputMode={elegido ? 'decimal' : undefined}
          maxLength={60}
        />
        <Campo
          id={`${prefijo}-monto`}
          aiId={`${prefijo}.monto`}
          etiqueta="Monto en soles"
          ayuda={
            elegido?.precio_venta
              ? 'Calculado con el precio; puedes cambiarlo'
              : 'Lo que cobras por este producto'
          }
          valor={monto}
          alCambiar={(valor) => {
            setMonto(valor)
            setMontoEscrito(true)
          }}
          inputMode="decimal"
          autoComplete="off"
          error={error}
        />
      </div>
      <Boton tipo="submit" aiId={`${prefijo}.agregar`} variante="secundario">
        Agregar producto
      </Boton>
    </form>
  )
}

function unidadEnPlural(unidad: ProductoCable['unidad']): string {
  return unidad === 'unidad' ? 'unidades' : unidad === 'kg' ? 'kilos' : 'litros'
}

export function FormularioNuevaOrden({ alTerminar }: { alTerminar: () => void }) {
  const abrirOrden = useVentas((estado) => estado.abrirOrden)
  const [nombre, setNombre] = useState('')

  return (
    <Tarjeta aiId="ventas.nueva-orden">
      <form
        className={estilos.formulario}
        onSubmit={(evento) => {
          evento.preventDefault()
          void abrirOrden({ nombreOrden: nombre.trim() || undefined })
          alTerminar()
        }}
      >
        <Campo
          id="nueva-orden-nombre"
          aiId="ventas.nueva-orden.nombre"
          etiqueta="Nombre de la orden (opcional)"
          ayuda="Por ejemplo: Mesa 2, Restaurante Doña Carmen"
          valor={nombre}
          alCambiar={setNombre}
          autoFocus
          maxLength={120}
        />
        <div className={estilos.accionesCabecera}>
          <Boton tipo="submit" aiId="ventas.nueva-orden.abrir">
            Abrir orden
          </Boton>
          <Boton aiId="ventas.nueva-orden.cancelar" variante="discreto" onClick={alTerminar}>
            Cancelar
          </Boton>
        </div>
      </form>
    </Tarjeta>
  )
}

export function FormularioVentaRapida({ alTerminar }: { alTerminar: () => void }) {
  const ventaRapida = useVentas((estado) => estado.ventaRapida)
  const [monto, setMonto] = useState('')
  const [error, setError] = useState<string | null>(null)

  const registrar = (metodo: MetodoPago) => {
    const centimos = leerMontoEscrito(monto)
    if (centimos === null || centimos === 0) return setError('Escribe el monto cobrado, por ejemplo 20')
    void ventaRapida(centimos, metodo)
    alTerminar()
  }

  return (
    <Tarjeta aiId="ventas.venta-rapida">
      <div className={estilos.formulario}>
        <Campo
          id="venta-rapida-monto"
          aiId="ventas.venta-rapida.monto"
          etiqueta="¿Cuánto cobraste?"
          ayuda="Solo el monto. El detalle lo completas después, cuando tengas un momento."
          valor={monto}
          alCambiar={setMonto}
          inputMode="decimal"
          autoFocus
          error={error}
        />
        <div className={estilos.accionesCabecera}>
          <Boton aiId="ventas.venta-rapida.efectivo" onClick={() => registrar('efectivo')}>
            Cobré en efectivo
          </Boton>
          <Boton aiId="ventas.venta-rapida.yape" variante="secundario" onClick={() => registrar('yape_plin')}>
            Cobré con Yape o Plin
          </Boton>
          <Boton aiId="ventas.venta-rapida.cancelar" variante="discreto" onClick={alTerminar}>
            Cancelar
          </Boton>
        </div>
      </div>
    </Tarjeta>
  )
}

/** Elegir (o registrar) el cliente al que se le fía. */
export function SelectorCliente({
  alElegir,
  alCancelar,
}: {
  alElegir: (cliente: ClienteCable) => void
  alCancelar: () => void
}) {
  const clientes = useVentas((estado) => estado.clientes)
  const buscarClientes = useVentas((estado) => estado.buscarClientes)
  const crearCliente = useVentas((estado) => estado.crearCliente)
  const [buscado, setBuscado] = useState('')
  const [telefono, setTelefono] = useState('')
  const [registrando, setRegistrando] = useState(false)

  useEffect(() => {
    const espera = window.setTimeout(() => void buscarClientes(buscado), 250)
    return () => window.clearTimeout(espera)
  }, [buscado, buscarClientes])

  return (
    <Tarjeta aiId="ventas.selector-cliente">
      <div className={estilos.formulario}>
        <Campo
          id="selector-cliente-nombre"
          aiId="ventas.selector-cliente.buscar"
          etiqueta="¿A quién le fías?"
          ayuda="Escribe parte del nombre"
          valor={buscado}
          alCambiar={setBuscado}
          autoFocus
          autoComplete="off"
          maxLength={120}
        />
        <ul className={estilos.resultados} aria-label="Clientes encontrados">
          {clientes.map((cliente) => (
            <li key={cliente.uuid}>
              <Boton
                aiId={`ventas.selector-cliente.cliente-${cliente.uuid}`}
                variante="discreto"
                anchoCompleto
                onClick={() => alElegir(cliente)}
              >
                {cliente.nombre}
              </Boton>
            </li>
          ))}
        </ul>
        {clientes.length === 0 && buscado.trim() && <Nota>No hay clientes con ese nombre todavía.</Nota>}

        {registrando ? (
          <>
            <Campo
              id="selector-cliente-telefono"
              aiId="ventas.selector-cliente.telefono"
              etiqueta="Teléfono (opcional)"
              valor={telefono}
              alCambiar={setTelefono}
              inputMode="tel"
              maxLength={20}
            />
            <Boton
              aiId="ventas.selector-cliente.guardar"
              deshabilitado={!buscado.trim()}
              onClick={() => void crearCliente(buscado.trim(), telefono.trim()).then(alElegir)}
            >
              {buscado.trim() ? `Registrar a ${buscado.trim()}` : 'Escribe el nombre para registrarlo'}
            </Boton>
          </>
        ) : (
          <Boton
            aiId="ventas.selector-cliente.nuevo"
            variante="secundario"
            onClick={() => setRegistrando(true)}
          >
            Es un cliente nuevo
          </Boton>
        )}
        <Boton aiId="ventas.selector-cliente.cancelar" variante="discreto" onClick={alCancelar}>
          Cancelar
        </Boton>
      </div>
    </Tarjeta>
  )
}
