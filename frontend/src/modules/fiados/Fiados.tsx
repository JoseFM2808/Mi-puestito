import { useCallback, useEffect, useState } from 'react'
import { SinConexion, pedir } from '../../api/cliente'
import { aSoles, leerClienteConDeuda, leerMontoEscrito, type ClienteConDeudaCable } from '../../api/contrato'
import { OperacionesRechazadas } from '../../componentes/sincronizacion/EstadoSincronizacion'
import { alAplicarOperacion, encolar } from '../../sincronizacion/cola'
import { senalar } from '../../componentes/asistente/senalar'
import { useBorradorAsistente } from '../../stores/borradorAsistente'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Monto, Nota, Tarjeta, TituloPagina } from '../../ui/componentes'
import { productoPorNombre } from '../inventario/nombres'
import estilos from './Fiados.module.css'

/**
 * Fiados: quién debe y cuánto (deuda derivada en el servidor: Σ fiado −
 * Σ abonos), y registrar un abono. El abono se guarda aunque no haya red.
 */
export function Fiados() {
  const proyecto = useSesion((estado) => estado.proyecto)
  const [clientes, setClientes] = useState<ClienteConDeudaCable[]>([])
  const [sinConexion, setSinConexion] = useState(false)
  const [abonando, setAbonando] = useState<string | null>(null)
  const [monto, setMonto] = useState('')
  // En efectivo o por Yape: así el abono suma en el lugar correcto de la caja (D-24)
  const [medio, setMedio] = useState<'efectivo' | 'yape_plin'>('efectivo')
  const [error, setError] = useState<string | null>(null)
  const [avisos, setAvisos] = useState<string[]>([])
  const [llenadoPorAsistente, setLlenadoPorAsistente] = useState(false)
  const formularioAsistente = useBorradorAsistente((estado) => estado.formulario)

  const cargar = useCallback(async () => {
    try {
      setClientes(await pedir<ClienteConDeudaCable[]>('GET', '/api/ventas/fiados'))
      setSinConexion(false)
    } catch (fallo) {
      if (!(fallo instanceof SinConexion)) throw fallo
      setSinConexion(true)
    }
  }, [])

  useEffect(() => {
    void cargar()
    return alAplicarOperacion((operacion, respuesta) => {
      if (operacion.ruta !== '/api/ventas/abonos') return
      const avisosAbono = (respuesta as { avisos?: string[] } | undefined)?.avisos ?? []
      if (avisosAbono.length) setAvisos((actuales) => [...actuales, ...avisosAbono])
      void cargar()
    })
  }, [cargar])

  // El Asistente dejó un pago llenado (D-28): se abre en la tarjeta de ese cliente, sin guardar
  useEffect(() => {
    if (!proyecto || clientes.length === 0 || formularioAsistente?.formulario.tipo !== 'abono') return
    const pedido = useBorradorAsistente.getState().tomarFormulario('abono', proyecto)
    if (!pedido?.cliente) return
    const cliente = productoPorNombre(clientes, pedido.cliente)
    if (!cliente) {
      setAvisos((actuales) => [...actuales, `No encontré a «${pedido.cliente}» entre los que te deben.`])
      return
    }
    setAbonando(cliente.uuid)
    setMonto(pedido.monto ?? '')
    setMedio(pedido.medio ?? 'efectivo')
    setError(null)
    setLlenadoPorAsistente(true)
    void senalar(`fiados.cliente-${cliente.uuid}`)
  }, [proyecto, clientes, formularioAsistente])

  const total = clientes.reduce((suma, cliente) => suma + leerClienteConDeuda(cliente).deuda, 0)

  const registrarAbono = (cliente: ClienteConDeudaCable) => {
    const centimos = leerMontoEscrito(monto)
    if (!centimos) return setError('Escribe cuánto pagó, por ejemplo 10')
    if (!proyecto) return
    void encolar(proyecto, {
      metodo: 'POST',
      ruta: '/api/ventas/abonos',
      descripcion: `Abono de ${cliente.nombre}`,
      cuerpo: {
        uuid: crypto.randomUUID(),
        cliente_uuid: cliente.uuid,
        monto: aSoles(centimos),
        metodo_pago: medio,
      },
    })
    // Se refleja al instante; el servidor confirma al sincronizar
    setClientes((actuales) =>
      actuales.map((c) =>
        c.uuid === cliente.uuid ? { ...c, deuda: aSoles(leerClienteConDeuda(c).deuda - centimos) } : c,
      ),
    )
    setAbonando(null)
    setMonto('')
    setMedio('efectivo')
    setError(null)
    setLlenadoPorAsistente(false)
  }

  return (
    <main className={estilos.pantalla} data-ai-id="fiados">
      <TituloPagina ayuda="Quién te debe y cuánto. Cuando alguien te pague, toca su nombre y anota el pago.">
        Fiados
      </TituloPagina>
      <OperacionesRechazadas alDescartar={() => void cargar()} />
      {avisos.map((aviso, indice) => (
        <Aviso key={`${indice}-${aviso}`} tipo="pendiente">
          {aviso}
        </Aviso>
      ))}
      {sinConexion && (
        <Aviso tipo="info" aiId="fiados.sin-conexion">
          Sin conexión: la lista se actualiza al volver la red. Los abonos que registres se guardan igual.
        </Aviso>
      )}

      <Tarjeta aiId="fiados.total" className={estilos.resumen}>
        <span className={estilos.etiqueta}>Te deben en total</span>
        <Monto centimos={total} tamano="grande" tono="deuda" />
        <Nota>
          {clientes.length} {clientes.length === 1 ? 'cliente debe' : 'clientes deben'}
        </Nota>
      </Tarjeta>

      {clientes.length === 0 && !sinConexion && <Nota>Nadie te debe. ¡Buen trabajo cobrando!</Nota>}

      <ul className={estilos.lista}>
        {clientes.map((cable) => {
          const cliente = leerClienteConDeuda(cable)
          const id = `fiados.cliente-${cliente.uuid}`
          return (
            <li key={cliente.uuid}>
              <Tarjeta aiId={id} className={estilos.cliente}>
                <div className={estilos.fila}>
                  <span className={estilos.nombre}>{cliente.nombre}</span>
                  <span>
                    debe <Monto centimos={cliente.deuda} tamano="orden" tono="deuda" />
                  </span>
                </div>
                {cliente.limiteCredito !== null && (
                  <Nota>
                    Límite de crédito: <Monto centimos={cliente.limiteCredito} />
                    {cliente.deuda > cliente.limiteCredito ? ' (lo superó)' : ''}
                  </Nota>
                )}
                {abonando === cliente.uuid ? (
                  <form
                    className={estilos.abono}
                    onSubmit={(evento) => {
                      evento.preventDefault()
                      registrarAbono(cable)
                    }}
                    noValidate
                  >
                    <Campo
                      id={`abono-${cliente.uuid}`}
                      aiId={`${id}.monto-abono`}
                      etiqueta={`¿Cuánto pagó ${cliente.nombre}?`}
                      valor={monto}
                      alCambiar={setMonto}
                      inputMode="decimal"
                      autoFocus
                      error={error}
                    />
                    {llenadoPorAsistente && (
                      <Nota>
                        Lo llenó el Asistente: revísalo y toca «Guardar abono». Aún no se guardó nada.
                      </Nota>
                    )}
                    <div className={estilos.fila}>
                      {(['efectivo', 'yape_plin'] as const).map((opcion) => (
                        <Boton
                          key={opcion}
                          aiId={`${id}.medio-${opcion}`}
                          variante="secundario"
                          presionado={medio === opcion}
                          onClick={() => setMedio(opcion)}
                        >
                          {opcion === 'efectivo' ? 'Pagó en efectivo' : 'Pagó por Yape o Plin'}
                        </Boton>
                      ))}
                    </div>
                    <div className={estilos.fila}>
                      <Boton tipo="submit" aiId={`${id}.guardar-abono`}>
                        Guardar abono
                      </Boton>
                      <Boton
                        aiId={`${id}.cancelar-abono`}
                        variante="discreto"
                        onClick={() => {
                          setAbonando(null)
                          setLlenadoPorAsistente(false)
                        }}
                      >
                        Cancelar
                      </Boton>
                    </div>
                  </form>
                ) : (
                  <Boton
                    aiId={`${id}.abonar`}
                    variante="secundario"
                    onClick={() => {
                      setAbonando(cliente.uuid)
                      setMonto('')
                      setMedio('efectivo')
                      setError(null)
                      setLlenadoPorAsistente(false)
                    }}
                  >
                    Registrar un pago
                  </Boton>
                )}
              </Tarjeta>
            </li>
          )
        })}
      </ul>
    </main>
  )
}
