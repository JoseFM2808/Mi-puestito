import { useSesion } from '../../stores/sesion'
import { descartarRechazada, useSincronizacion } from '../../sincronizacion/cola'
import { Aviso, Boton } from '../../ui/componentes'
import estilos from './EstadoSincronizacion.module.css'

/**
 * Indicador "sin conexión / sincronizando" (Fase 5) y operaciones que el
 * servidor rechazó. Siempre en palabras: el operador debe entender qué pasó
 * con su venta sin saber qué es una cola.
 */
export function IndicadorConexion() {
  const { pendientes, sinConexion, sincronizando } = useSincronizacion()
  if (pendientes === 0 && !sinConexion) return null
  const texto = sinConexion
    ? `Sin conexión. ${pendientes} ${pendientes === 1 ? 'cambio guardado' : 'cambios guardados'} en esta tablet; se enviarán solos.`
    : sincronizando
      ? `Enviando ${pendientes} ${pendientes === 1 ? 'cambio' : 'cambios'}…`
      : `${pendientes} ${pendientes === 1 ? 'cambio' : 'cambios'} por enviar.`
  return (
    <p className={estilos.indicador} data-ai-id="sincronizacion.estado" role="status">
      {texto}
    </p>
  )
}

export function OperacionesRechazadas({ alDescartar }: { alDescartar?: () => void }) {
  const rechazadas = useSincronizacion((estado) => estado.rechazadas)
  const proyecto = useSesion((estado) => estado.proyecto)
  if (!proyecto || rechazadas.length === 0) return null
  return (
    <div className={estilos.lista} data-ai-id="sincronizacion.rechazadas">
      {rechazadas.map((operacion) => (
        <div key={operacion.id} className={estilos.fila}>
          <Aviso tipo="error">
            No se pudo guardar «{operacion.descripcion}»: {operacion.error}
          </Aviso>
          <Boton
            aiId={`sincronizacion.rechazada-${operacion.id}.entendido`}
            variante="discreto"
            onClick={() => {
              if (operacion.id) void descartarRechazada(proyecto, operacion.id).then(alDescartar)
            }}
          >
            Entendido
          </Boton>
        </div>
      ))}
    </div>
  )
}
