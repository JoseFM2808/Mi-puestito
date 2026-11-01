import { useEffect, useState } from 'react'
import { ErrorApi, SinConexion, pedir } from '../../api/cliente'
import type { AccionSugeridaCable, EstadoAsistenteCable, RespuestaAsistenteCable } from '../../api/contrato'
import { PANTALLAS, useNavegacion, type Pantalla } from '../../stores/navegacion'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Nota } from '../../ui/componentes'
import estilos from './Asistente.module.css'

/**
 * Panel del Asistente (AI Companion). Responde con el mismo resumen que ve
 * el operador en la Caja de hoy, nunca con datos de otro proyecto (lo
 * garantiza el backend con el token).
 *
 * - Recuerda la conversación: envía los últimos turnos como historial.
 * - Puede SUGERIR ir a una pantalla (ADR-037): aparece un botón con texto
 *   completo; el Asistente nunca navega ni registra nada por su cuenta.
 * - "Me sirvió" / "No me sirvió" ayuda a mejorar un futuro modelo local (ADR-038).
 * - Privacidad (ADR-034): el backend cambia los nombres de clientes y
 *   proveedores por códigos antes de enviar la pregunta al servicio externo.
 */

interface Mensaje {
  quienHabla: 'operador' | 'asistente'
  texto: string
  acciones?: AccionSugeridaCable[]
  idRespuesta?: string
  valorada?: boolean
}

const TURNOS_DE_MEMORIA = 6
const SALUDO = 'Hola, soy tu Asistente. Pregúntame por tu caja de hoy o cómo hacer algo en la app.'

/**
 * Pide la llave de IA dentro del programa (D-14). Va directo al servidor: nunca a la
 * cola offline ni al almacenamiento del navegador, y el campo se vacía al enviarla.
 */
function PedirLlave({ alGuardar }: { alGuardar: (estado: EstadoAsistenteCable) => void }) {
  const [llave, setLlave] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const guardar = async (evento: React.FormEvent) => {
    evento.preventDefault()
    if (!llave.trim() || guardando) return
    setGuardando(true)
    setError(null)
    try {
      alGuardar(await pedir<EstadoAsistenteCable>('POST', '/api/asistente/llave', { llave }))
    } catch (fallo) {
      setError(
        fallo instanceof ErrorApi
          ? fallo.detalle
          : 'No se pudo guardar. Revisa que el programa siga abierto.',
      )
    } finally {
      setLlave('')
      setGuardando(false)
    }
  }

  return (
    <form
      className={estilos.formulario}
      data-ai-id="asistente.configurar"
      onSubmit={(evento) => void guardar(evento)}
    >
      <Aviso tipo="info">
        Para usar el Asistente hace falta una llave de NVIDIA, que se crea en build.nvidia.com. Lo demás de la
        app funciona sin ella.
      </Aviso>
      {error && (
        <Aviso tipo="error" aiId="asistente.error-llave">
          {error}
        </Aviso>
      )}
      <Campo
        id="asistente-llave"
        aiId="asistente.llave"
        etiqueta="Pega aquí tu llave"
        ayuda="Se guarda cifrada en esta computadora y solo se usa para hablar con NVIDIA."
        type="password"
        autoComplete="off"
        valor={llave}
        alCambiar={setLlave}
      />
      <Boton tipo="submit" aiId="asistente.guardar-llave" variante="ia" deshabilitado={guardando}>
        {guardando ? 'Probando la llave…' : 'Guardar llave'}
      </Boton>
    </form>
  )
}

export function Asistente() {
  const esReal = useSesion((estado) => estado.esReal)
  const irA = useNavegacion((estado) => estado.irA)
  const [mensajes, setMensajes] = useState<Mensaje[]>([{ quienHabla: 'asistente', texto: SALUDO }])
  const [pregunta, setPregunta] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [estado, setEstado] = useState<EstadoAsistenteCable | null>(null)

  useEffect(() => {
    // Si esto falla (sin red), el panel sigue igual: el error real aparece al preguntar
    pedir<EstadoAsistenteCable>('GET', '/api/asistente/estado')
      .then(setEstado)
      .catch(() => {})
  }, [])

  const quitarLlave = () => {
    void pedir<EstadoAsistenteCable>('DELETE', '/api/asistente/llave')
      .then(setEstado)
      .catch(() => {})
  }

  const enviar = async (evento: React.FormEvent) => {
    evento.preventDefault()
    const texto = pregunta.trim()
    if (!texto || enviando) return

    // La memoria son los turnos reales (no el saludo), los más recientes
    const historial = mensajes
      .slice(1)
      .slice(-TURNOS_DE_MEMORIA)
      .map((m) => ({ rol: m.quienHabla, texto: m.texto }))
    setMensajes((actual) => [...actual, { quienHabla: 'operador', texto }])
    setPregunta('')
    setEnviando(true)
    try {
      const respuesta = await pedir<RespuestaAsistenteCable>('POST', '/api/asistente/preguntar', {
        mensaje: texto,
        historial,
      })
      setMensajes((actual) => [
        ...actual,
        {
          quienHabla: 'asistente',
          texto: respuesta.respuesta,
          acciones: respuesta.acciones,
          idRespuesta: respuesta.id_respuesta,
        },
      ])
    } catch (error) {
      const aviso =
        error instanceof SinConexion
          ? 'No pude conectarme. El Asistente necesita internet; lo demás de la app sigue funcionando.'
          : error instanceof ErrorApi
            ? error.detalle
            : 'El Asistente no pudo responder ahora mismo.'
      setMensajes((actual) => [...actual, { quienHabla: 'asistente', texto: aviso }])
    } finally {
      setEnviando(false)
    }
  }

  const valorar = (indice: number, util: boolean) => {
    const mensaje = mensajes[indice]
    if (!mensaje.idRespuesta || mensaje.valorada) return
    setMensajes((actual) => actual.map((m, i) => (i === indice ? { ...m, valorada: true } : m)))
    // Si falla no pasa nada: la valoración es una ayuda, no una operación del negocio
    void pedir('POST', '/api/asistente/valoracion', { id_respuesta: mensaje.idRespuesta, util }).catch(
      () => {},
    )
  }

  const esPantalla = (pantalla: string): pantalla is Pantalla => PANTALLAS.some((p) => p.clave === pantalla)

  if (estado && !estado.listo && estado.puede_guardar_llave) {
    return (
      <section className={estilos.asistente} data-ai-id="asistente" aria-label="Asistente">
        <PedirLlave alGuardar={setEstado} />
      </section>
    )
  }

  return (
    <section className={estilos.asistente} data-ai-id="asistente" aria-label="Asistente">
      {esReal && (
        <Aviso tipo="info" aiId="asistente.privacidad">
          Tus preguntas se responden con un servicio de inteligencia artificial por internet. Antes de
          enviarlas, los nombres de tus clientes y proveedores se cambian por códigos: ese servicio nunca los
          ve.
        </Aviso>
      )}
      <div className={estilos.mensajes} role="log" aria-live="polite" data-ai-id="asistente.conversacion">
        {mensajes.map((mensaje, indice) => (
          <div
            key={indice}
            className={`${estilos.turno} ${mensaje.quienHabla === 'asistente' ? estilos.turnoIa : estilos.turnoOperador}`}
          >
            <p
              className={`${estilos.burbuja} ${mensaje.quienHabla === 'asistente' ? estilos.burbujaIa : estilos.burbujaOperador}`}
            >
              {mensaje.texto}
            </p>
            {mensaje.acciones?.map((accion) => {
              const destino = accion.pantalla
              // Solo pantallas que existen: lo que el modelo invente no se muestra
              if (!esPantalla(destino)) return null
              return (
                <Boton
                  key={destino}
                  aiId={`asistente.accion-${indice}-${destino}`}
                  variante="secundario"
                  onClick={() => irA(destino)}
                >
                  {accion.etiqueta}
                </Boton>
              )
            })}
            {mensaje.idRespuesta && (
              <div className={estilos.valoracion}>
                {mensaje.valorada ? (
                  <span className={estilos.gracias}>Gracias por avisar.</span>
                ) : (
                  <>
                    <Boton
                      aiId={`asistente.sirvio-${indice}`}
                      variante="discreto"
                      onClick={() => valorar(indice, true)}
                    >
                      Me sirvió
                    </Boton>
                    <Boton
                      aiId={`asistente.no-sirvio-${indice}`}
                      variante="discreto"
                      onClick={() => valorar(indice, false)}
                    >
                      No me sirvió
                    </Boton>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
        {enviando && <p className={`${estilos.burbuja} ${estilos.burbujaIa}`}>Pensando…</p>}
      </div>

      <form className={estilos.formulario} onSubmit={(evento) => void enviar(evento)}>
        <Campo
          id="asistente-pregunta"
          aiId="asistente.pregunta"
          etiqueta="Escríbele al Asistente"
          placeholder="Por ejemplo: ¿cuánto vendí hoy?"
          valor={pregunta}
          alCambiar={setPregunta}
          maxLength={500}
          autoComplete="off"
        />
        <Boton tipo="submit" aiId="asistente.enviar" variante="ia" deshabilitado={enviando}>
          Enviar
        </Boton>
      </form>
      {estado?.llave_guardada && estado.puede_guardar_llave && (
        <div className={estilos.valoracion}>
          <Nota>Usa la llave guardada en esta computadora.</Nota>
          <Boton aiId="asistente.quitar-llave" variante="discreto" onClick={quitarLlave}>
            Quitar la llave
          </Boton>
        </div>
      )}
    </section>
  )
}
