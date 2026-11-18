import { useCallback, useEffect, useState } from 'react'
import { SinConexion, pedir } from '../../api/cliente'
import { aSoles, leerClienteConDeuda, leerMontoEscrito, type ClienteConDeudaCable } from '../../api/contrato'
import { OperacionesRechazadas } from '../../componentes/sincronizacion/EstadoSincronizacion'
import { alAplicarOperacion, encolar } from '../../sincronizacion/cola'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Monto, Nota, Tarjeta, TituloPagina } from '../../ui/componentes'
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
  const [error, setError] = useState<string | null>(null)
  const [avisos, setAvisos] = useState<string[]>([])

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
        metodo_pago: 'efectivo',
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
    setError(null)
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
                    <div className={estilos.fila}>
                      <Boton tipo="submit" aiId={`${id}.guardar-abono`}>
                        Guardar abono
                      </Boton>
                      <Boton
                        aiId={`${id}.cancelar-abono`}
                        variante="discreto"
                        onClick={() => setAbonando(null)}
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
                      setError(null)
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
