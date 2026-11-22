import { useCallback, useEffect, useState } from 'react'
import { ErrorApi, SinConexion, pedir } from '../../api/cliente'
import type { RecuerdoCable } from '../../api/contrato'
import { Aviso, Boton, Nota, Tarjeta, TituloSeccion } from '../../ui/componentes'
import estilos from './Asistente.module.css'

/**
 * "Lo que el Asistente recuerda" (D-26, ADR-052). Lo que el operador le pidió recordar vive en la
 * computadora del negocio, no en el navegador: aquí se ve y se olvida, uno por uno o todo. Sin red
 * con el programa no se puede ver ni cambiar (el Asistente tampoco responde sin ella).
 */
export function Recuerdos({ alCerrar }: { alCerrar: () => void }) {
  const [recuerdos, setRecuerdos] = useState<RecuerdoCable[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirmarTodo, setConfirmarTodo] = useState(false)

  const cargar = useCallback(() => {
    setError(null)
    pedir<RecuerdoCable[]>('GET', '/api/asistente/recuerdos')
      .then(setRecuerdos)
      .catch((fallo: unknown) => setError(explicar(fallo)))
  }, [])

  useEffect(cargar, [cargar])

  const olvidar = async (ruta: string) => {
    setError(null)
    try {
      await pedir('DELETE', ruta)
      setConfirmarTodo(false)
      cargar()
    } catch (fallo) {
      setError(explicar(fallo))
    }
  }

  return (
    <Tarjeta aiId="asistente.recuerdos" className={estilos.recuerdos}>
      <TituloSeccion>Lo que el Asistente recuerda</TituloSeccion>
      <Nota>
        Cuando le dices «acuérdate que…» o le cuentas algo de tu negocio que no cambia, lo guarda aquí para
        atenderte mejor. Se queda en esta computadora y puedes olvidarlo cuando quieras.
      </Nota>
      {error && (
        <Aviso tipo="error" aiId="asistente.recuerdos-error">
          {error}
        </Aviso>
      )}
      {recuerdos === null && !error && <Nota>Buscando…</Nota>}
      {recuerdos?.length === 0 && <Nota>Todavía no recuerda nada.</Nota>}
      {recuerdos && recuerdos.length > 0 && (
        <ul className={estilos.listaRecuerdos}>
          {recuerdos.map((recuerdo) => (
            <li key={recuerdo.uuid} className={estilos.recuerdo}>
              <span>{recuerdo.texto}</span>
              <Boton
                aiId={`asistente.olvidar-${recuerdo.uuid}`}
                variante="discreto"
                onClick={() => void olvidar(`/api/asistente/recuerdos/${recuerdo.uuid}`)}
              >
                Olvidar esto
              </Boton>
            </li>
          ))}
        </ul>
      )}
      <div className={estilos.pie}>
        {recuerdos && recuerdos.length > 0 && !confirmarTodo && (
          <Boton aiId="asistente.olvidar-todo" variante="discreto" onClick={() => setConfirmarTodo(true)}>
            Olvidar todo
          </Boton>
        )}
        {confirmarTodo && (
          <>
            <Nota>¿Seguro? El Asistente olvidará todo lo que le contaste.</Nota>
            <Boton
              aiId="asistente.confirmar-olvidar-todo"
              variante="peligro"
              onClick={() => void olvidar('/api/asistente/recuerdos')}
            >
              Sí, olvidar todo
            </Boton>
            <Boton
              aiId="asistente.cancelar-olvidar-todo"
              variante="secundario"
              onClick={() => setConfirmarTodo(false)}
            >
              No, dejarlo
            </Boton>
          </>
        )}
        <Boton aiId="asistente.cerrar-recuerdos" variante="secundario" onClick={alCerrar}>
          Volver a la conversación
        </Boton>
      </div>
    </Tarjeta>
  )
}

function explicar(fallo: unknown): string {
  if (fallo instanceof SinConexion)
    return 'No pude conectarme con el programa. Inténtalo cuando vuelva la conexión.'
  if (fallo instanceof ErrorApi) return fallo.detalle
  return 'No se pudo hacer ahora. Intenta de nuevo.'
}
