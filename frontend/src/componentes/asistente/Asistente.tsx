import { useEffect, useRef, useState } from 'react'
import { ErrorApi, SinConexion, pedir } from '../../api/cliente'
import type { EstadoAsistenteCable, RespuestaAsistenteCable } from '../../api/contrato'
import { useConversacion } from '../../stores/conversacion'
import { PANTALLAS, useNavegacion, type Pantalla } from '../../stores/navegacion'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Nota, TituloPagina } from '../../ui/componentes'
import estilos from './Asistente.module.css'

/**
 * El Asistente (AI Companion), en dos formas que comparten la MISMA conversación:
 *
 * - **Apartado** (`Asistente`): pantalla de chat completa, con su opción en el menú.
 * - **Ventana flotante** (`AsistenteFlotante`): sobre la pantalla actual. Sigue abierta
 *   al cambiar de pantalla, para que el operador vea la app mientras el Asistente lo guía
 *   o, más adelante, actúa en ella (Design-System §6 ter, ADR-046).
 *
 * Responde con el mismo resumen que ve el operador en la Caja de hoy, nunca con datos de
 * otro proyecto (lo garantiza el backend con el token). Puede SUGERIR ir a una pantalla
 * (ADR-037): un botón con texto completo que el operador decide tocar. "Me sirvió" / "No me
 * sirvió" ayuda a mejorar un futuro modelo local (ADR-038). Privacidad (ADR-034): el backend
 * cambia los nombres de clientes y proveedores por códigos antes de enviar la pregunta.
 */

const TURNOS_DE_MEMORIA = 6

/** Para empezar sin tener que pensar qué escribir: un toque y se pregunta */
const PREGUNTAS_SUGERIDAS = [
  '¿Cuánto vendí hoy?',
  '¿Quién me debe más?',
  '¿Qué pedidos llegan mañana?',
  '¿Cómo registro una venta?',
]

/** Si el Asistente puede responder, y si la llave se puede guardar desde aquí (D-14). */
function useEstadoAsistente() {
  const [estado, setEstado] = useState<EstadoAsistenteCable | null>(null)
  useEffect(() => {
    // Si esto falla (sin red), todo sigue igual: el error real aparece al preguntar
    pedir<EstadoAsistenteCable>('GET', '/api/asistente/estado')
      .then(setEstado)
      .catch(() => {})
  }, [])
  return [estado, setEstado] as const
}

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
      className={estilos.configurar}
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

/**
 * La conversación: mensajes, preguntas sugeridas y la caja para escribir. La usan el
 * apartado y la ventana; `prefijo` separa sus `data-ai-id` y los ids de los campos.
 */
function Conversacion({ prefijo }: { prefijo: 'asistente' | 'asistente-ventana' }) {
  const proyecto = useSesion((estado) => estado.proyecto)
  const irA = useNavegacion((estado) => estado.irA)
  const { mensajes, enviando, usarProyecto, agregar, marcarValorada, setEnviando } = useConversacion()
  const [pregunta, setPregunta] = useState('')
  const final = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (proyecto) usarProyecto(proyecto)
  }, [proyecto, usarProyecto])

  // Lo último dicho siempre a la vista, sin tener que bajar a buscarlo
  useEffect(() => {
    final.current?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
  }, [mensajes.length, enviando])

  const preguntar = async (texto: string) => {
    if (!texto || enviando) return
    // La memoria son los turnos reales (no el saludo), los más recientes
    const historial = mensajes
      .slice(1)
      .slice(-TURNOS_DE_MEMORIA)
      .map((m) => ({ rol: m.quienHabla, texto: m.texto }))
    agregar({ quienHabla: 'operador', texto })
    setPregunta('')
    setEnviando(true)
    try {
      const respuesta = await pedir<RespuestaAsistenteCable>('POST', '/api/asistente/preguntar', {
        mensaje: texto,
        historial,
      })
      agregar({
        quienHabla: 'asistente',
        texto: respuesta.respuesta,
        acciones: respuesta.acciones,
        idRespuesta: respuesta.id_respuesta,
      })
    } catch (error) {
      const aviso =
        error instanceof SinConexion
          ? 'No pude conectarme. El Asistente necesita internet; lo demás de la app sigue funcionando.'
          : error instanceof ErrorApi
            ? error.detalle
            : 'El Asistente no pudo responder ahora mismo.'
      agregar({ quienHabla: 'asistente', texto: aviso })
    } finally {
      setEnviando(false)
    }
  }

  const valorar = (indice: number, util: boolean) => {
    const mensaje = mensajes[indice]
    if (!mensaje.idRespuesta || mensaje.valorada) return
    marcarValorada(indice)
    // Si falla no pasa nada: la valoración es una ayuda, no una operación del negocio
    void pedir('POST', '/api/asistente/valoracion', { id_respuesta: mensaje.idRespuesta, util }).catch(
      () => {},
    )
  }

  const esPantalla = (pantalla: string): pantalla is Pantalla => PANTALLAS.some((p) => p.clave === pantalla)
  const soloSaludo = mensajes.length === 1

  return (
    <>
      <div className={estilos.mensajes} role="log" aria-live="polite" data-ai-id={`${prefijo}.conversacion`}>
        {mensajes.map((mensaje, indice) => (
          <div
            key={indice}
            className={`${estilos.turno} ${mensaje.quienHabla === 'asistente' ? estilos.turnoIa : estilos.turnoOperador}`}
          >
            <span className={estilos.quien}>{mensaje.quienHabla === 'asistente' ? 'Asistente' : 'Tú'}</span>
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
                  aiId={`${prefijo}.accion-${indice}-${destino}`}
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
                      aiId={`${prefijo}.sirvio-${indice}`}
                      variante="discreto"
                      onClick={() => valorar(indice, true)}
                    >
                      Me sirvió
                    </Boton>
                    <Boton
                      aiId={`${prefijo}.no-sirvio-${indice}`}
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
        {enviando && (
          <div className={`${estilos.turno} ${estilos.turnoIa}`}>
            <span className={estilos.quien}>Asistente</span>
            <p className={`${estilos.burbuja} ${estilos.burbujaIa}`}>Pensando…</p>
          </div>
        )}
        {soloSaludo && (
          <section
            className={estilos.sugerencias}
            aria-label="Preguntas para empezar"
            data-ai-id={`${prefijo}.sugerencias`}
          >
            <Nota>Toca una pregunta para empezar:</Nota>
            <div className={estilos.listaSugerencias}>
              {PREGUNTAS_SUGERIDAS.map((texto, indice) => (
                <Boton
                  key={texto}
                  aiId={`${prefijo}.sugerencia-${indice}`}
                  variante="secundario"
                  deshabilitado={enviando}
                  onClick={() => void preguntar(texto)}
                >
                  {texto}
                </Boton>
              ))}
            </div>
          </section>
        )}
        <div ref={final} />
      </div>

      <form
        className={estilos.formulario}
        onSubmit={(evento) => {
          evento.preventDefault()
          void preguntar(pregunta.trim())
        }}
      >
        <Campo
          id={`${prefijo}-pregunta`}
          aiId={`${prefijo}.pregunta`}
          etiqueta="Escribe tu pregunta"
          placeholder="Por ejemplo: ¿cuánto vendí hoy?"
          valor={pregunta}
          alCambiar={setPregunta}
          maxLength={500}
          autoComplete="off"
        />
        <Boton
          tipo="submit"
          aiId={`${prefijo}.enviar`}
          variante="ia"
          deshabilitado={enviando || !pregunta.trim()}
        >
          Enviar pregunta
        </Boton>
      </form>
    </>
  )
}

/** El apartado: pantalla de chat completa. */
export function Asistente() {
  const esReal = useSesion((estado) => estado.esReal)
  const asistenteAVentana = useNavegacion((estado) => estado.asistenteAVentana)
  const { mensajes, enviando, empezarDeNuevo } = useConversacion()
  const [estado, setEstado] = useEstadoAsistente()

  const quitarLlave = () => {
    void pedir<EstadoAsistenteCable>('DELETE', '/api/asistente/llave')
      .then(setEstado)
      .catch(() => {})
  }

  return (
    <main className={estilos.pantalla} data-ai-id="asistente" aria-label="Asistente">
      <TituloPagina ayuda="Escríbele como le hablarías a una persona. Te responde con las cifras de tu caja y te dice dónde hacer cada cosa; nunca registra nada por ti.">
        Asistente
      </TituloPagina>

      {estado && !estado.listo && estado.puede_guardar_llave ? (
        <PedirLlave alGuardar={setEstado} />
      ) : (
        <>
          <Boton aiId="asistente.a-ventana" variante="secundario" onClick={asistenteAVentana}>
            Usar en ventana mientras trabajo
          </Boton>
          {esReal && (
            <Aviso tipo="info" aiId="asistente.privacidad">
              Tus preguntas se responden con un servicio de inteligencia artificial por internet. Antes de
              enviarlas, los nombres de tus clientes y proveedores se cambian por códigos: ese servicio nunca
              los ve.
            </Aviso>
          )}
          <Conversacion prefijo="asistente" />
          <div className={estilos.pie}>
            {mensajes.length > 1 && (
              <Boton
                aiId="asistente.empezar-de-nuevo"
                variante="discreto"
                deshabilitado={enviando}
                onClick={empezarDeNuevo}
              >
                Empezar una conversación nueva
              </Boton>
            )}
            {estado?.llave_guardada && estado.puede_guardar_llave && (
              <>
                <Nota>Usa la llave guardada en esta computadora.</Nota>
                <Boton aiId="asistente.quitar-llave" variante="discreto" onClick={quitarLlave}>
                  Quitar la llave
                </Boton>
              </>
            )}
          </div>
        </>
      )}
    </main>
  )
}

/**
 * La ventana flotante: el mismo Asistente sobre la pantalla actual. No tapa la barra ni el
 * menú, y sigue abierta al cambiar de pantalla. En teléfono ocupa la mitad de abajo.
 */
export function AsistenteFlotante() {
  const irA = useNavegacion((estado) => estado.irA)
  const cerrar = useNavegacion((estado) => estado.cerrarAsistenteFlotante)
  const [estado] = useEstadoAsistente()
  const panel = useRef<HTMLElement>(null)

  useEffect(() => {
    panel.current?.focus()
  }, [])

  const sinLlave = estado && !estado.listo && estado.puede_guardar_llave

  return (
    <section
      ref={panel}
      className={estilos.ventana}
      data-ai-id="asistente-ventana"
      role="dialog"
      aria-modal="false"
      aria-labelledby="titulo-asistente-ventana"
      tabIndex={-1}
    >
      <header className={estilos.cabeceraVentana}>
        <h2 id="titulo-asistente-ventana" className={estilos.tituloVentana}>
          Asistente
        </h2>
        <div className={estilos.accionesVentana}>
          <Boton aiId="asistente-ventana.ampliar" variante="discreto" onClick={() => irA('asistente')}>
            Pantalla completa
          </Boton>
          <Boton aiId="asistente-ventana.cerrar" variante="discreto" onClick={cerrar}>
            Cerrar
          </Boton>
        </div>
      </header>
      {sinLlave ? (
        <div className={estilos.cuerpoVentana}>
          <Nota>Falta configurar la llave del Asistente.</Nota>
          <Boton aiId="asistente-ventana.configurar" variante="ia" onClick={() => irA('asistente')}>
            Configurar el Asistente
          </Boton>
        </div>
      ) : (
        <div className={estilos.cuerpoVentana}>
          <Conversacion prefijo="asistente-ventana" />
        </div>
      )}
    </section>
  )
}
