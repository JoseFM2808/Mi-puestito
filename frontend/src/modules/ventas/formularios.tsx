import { useEffect, useState } from 'react'
import { leerMontoEscrito, type ClienteCable, type MetodoPago } from '../../api/contrato'
import { Boton, Campo, Nota, Tarjeta } from '../../ui/componentes'
import { useVentas } from './almacen'
import estilos from './Ventas.module.css'

/**
 * Formularios del módulo Ventas. Cada uno valida en palabras simples antes
 * de enviar y deja el foco donde el operador lo necesita.
 */

export function FormularioProducto({
  prefijo,
  alAgregar,
}: {
  /** Distingue los ids cuando hay más de un formulario en pantalla */
  prefijo: string
  alAgregar: (datos: { nombre: string; cantidad: string; centimos: number }) => void
}) {
  const [nombre, setNombre] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [monto, setMonto] = useState('')
  const [error, setError] = useState<string | null>(null)

  const enviar = (evento: React.FormEvent) => {
    evento.preventDefault()
    const centimos = leerMontoEscrito(monto)
    if (!nombre.trim()) return setError('Escribe qué producto vendiste.')
    if (centimos === null) return setError('Escribe el monto en soles, por ejemplo 12.50')
    alAgregar({ nombre: nombre.trim(), cantidad: cantidad.trim(), centimos })
    setNombre('')
    setCantidad('')
    setMonto('')
    setError(null)
  }

  return (
    <form className={estilos.formulario} onSubmit={enviar} noValidate>
      <Campo
        id={`${prefijo}-producto`}
        aiId={`${prefijo}.producto`}
        etiqueta="Producto"
        valor={nombre}
        alCambiar={setNombre}
        autoComplete="off"
        maxLength={120}
      />
      <div className={estilos.filaCampos}>
        <Campo
          id={`${prefijo}-cantidad`}
          aiId={`${prefijo}.cantidad`}
          etiqueta="Cantidad (opcional)"
          ayuda="Por ejemplo: 2 kg"
          valor={cantidad}
          alCambiar={setCantidad}
          autoComplete="off"
          maxLength={60}
        />
        <Campo
          id={`${prefijo}-monto`}
          aiId={`${prefijo}.monto`}
          etiqueta="Monto en soles"
          ayuda="Lo que cobras por este producto"
          valor={monto}
          alCambiar={setMonto}
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
