import { useEffect, useRef, useState } from 'react'
import { ErrorApi, SinConexion, pedir } from '../../api/cliente'
import type {
  AccionSugeridaCable,
  EstadoAsistenteCable,
  ProductoCable,
  RespuestaAsistenteCable,
} from '../../api/contrato'
import { useInventario } from '../../modules/inventario/almacen'
import { trozosConProductos } from '../../modules/inventario/nombres'
import { useBorradorAsistente } from '../../stores/borradorAsistente'
import { useConversacion } from '../../stores/conversacion'
import { PANTALLAS, useNavegacion, type Pantalla } from '../../stores/navegacion'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo, Nota, TituloPagina } from '../../ui/componentes'
import estilos from './Asistente.module.css'
import { useDictado } from './dictado'
import { estaALaVista, senalar } from './senalar'

/**
 * El Asistente (AI Companion), en dos formas que comparten la MISMA conversación:
 *
 * - **Apartado** (`Asistente`): pantalla de chat completa, con su opción en el menú.
 * - **Ventana flotante** (`AsistenteFlotante`): sobre la pantalla actual. Sigue abierta
 *   al cambiar de pantalla, para que el operador vea la app mientras el Asistente lo guía
 *   o, más adelante, actúa en ella (Design-System §6 ter, ADR-046).
 *
 * Responde con el mismo resumen que ve el operador en la Caja de hoy, nunca con datos de
 * otro proyecto (lo garantiza el backend con el token). Puede sugerir ir a una pantalla
 * (ADR-037): un botón con texto completo. Si el operador pidió ir o hacer algo ("quiero
 * registrar una compra"), la app abre esa pantalla sola y el Asistente queda en ventana, para
 * seguir hablando mientras se llenan los datos (ADR-047). Si pide registrar una venta, el
 * Asistente la LLENA en Ventas y el operador la revisa y la guarda: el Asistente nunca guarda
 * (ADR-049). Se le puede hablar en vez de escribir (dictado del navegador), y los productos
 * del inventario que nombra son enlaces a su tarjeta. "Me sirvió" / "No me
 * sirvió" ayuda a mejorar un futuro modelo local (ADR-038). Privacidad (ADR-034): el backend
 * cambia los nombres de clientes y proveedores por códigos antes de enviar la pregunta.
 */

const TURNOS_DE_MEMORIA = 6

/** Solo pantallas que existen: lo que el modelo invente no se muestra ni se abre */
const esPantalla = (pantalla: string): pantalla is Pantalla => PANTALLAS.some((p) => p.clave === pantalla)

const nombreDe = (pantalla: Pantalla) => PANTALLAS.find((p) => p.clave === pantalla)?.nombre ?? pantalla

/**
 * Sigue una acción del Asistente: lleva a su pantalla sin perder la conversación y, si es
 * "resaltar", señala esa parte. Solo navega y marca: nunca llena ni guarda nada (ADR-047).
 */
function seguir(accion: AccionSugeridaCable) {
  if (!esPantalla(accion.pantalla)) return
  const { pantalla, asistenteFlotante, llevarConAsistente } = useNavegacion.getState()
  if (pantalla !== accion.pantalla || !asistenteFlotante) llevarConAsistente(accion.pantalla)
  if (accion.tipo === 'resaltar' && accion.apartado) void senalar(accion.apartado)
}

/**
 * Lo que la app hace sola con una respuesta (solo la acción que el backend marcó
 * `automatica`: el operador pidió ir o hacer algo, o preguntó dónde está algo), y cómo se le
 * cuenta. Se dice solo lo que seguro pasó.
 */
function hacerSolo(acciones: AccionSugeridaCable[]): string | undefined {
  const pedida = acciones.find((accion) => accion.automatica && esPantalla(accion.pantalla))
  if (!pedida || !esPantalla(pedida.pantalla)) return undefined
  if (pedida.pantalla !== useNavegacion.getState().pantalla) {
    seguir(pedida)
    return `Abrí ${nombreDe(pedida.pantalla)}. Sigo aquí: llena los datos y pregúntame lo que necesites.`
  }
  // En la misma pantalla: se marca solo si esa parte está a la vista ahora (con un formulario
  // abierto, el botón de la pantalla no existe y no se busca)
  if (pedida.apartado && estaALaVista(pedida.apartado)) {
    seguir(pedida)
    return 'Te lo marqué en la pantalla.'
  }
  return undefined
}

const APARTADO_BORRADOR = 'ventas.borrador-asistente'

/** Lleva a Ventas, donde espera la orden que llenó el Asistente, y la señala */
function verBorrador() {
  const { pantalla, asistenteFlotante, llevarConAsistente } = useNavegacion.getState()
  if (pantalla !== 'ventas' || !asistenteFlotante) llevarConAsistente('ventas')
  void senalar(APARTADO_BORRADOR)
}

/** Lleva a la tarjeta del producto en Inventario y la señala */
function verProducto(producto: ProductoCable) {
  const { pantalla, asistenteFlotante, llevarConAsistente } = useNavegacion.getState()
  if (pantalla !== 'inventario' || !asistenteFlotante) llevarConAsistente('inventario')
  void senalar(`inventario.producto-${producto.uuid}`)
}

/**
 * Un mensaje (del Asistente o del operador), con cada producto del inventario que nombra convertido
 * en un enlace a su tarjeta ("Fideos Anita" → Inventario, marcado). El resto queda igual.
 */
function TextoConProductos({ texto, prefijo, indice }: { texto: string; prefijo: string; indice: number }) {
  const productos = useInventario((estado) => estado.productos)
  let numero = 0
  return (
    <>
      {trozosConProductos(texto, productos).map((trozo, i) => {
        if (!trozo.producto) return <span key={i}>{trozo.texto}</span>
        const producto = trozo.producto
        numero += 1
        return (
          <button
            key={i}
            type="button"
            className={estilos.enlaceProducto}
            data-ai-id={`${prefijo}.producto-${indice}-${numero}`}
            title={`Ver ${producto.nombre} en Inventario`}
            onClick={() => verProducto(producto)}
          >
            {trozo.texto}
          </button>
        )
      })}
    </>
  )
}

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
  const esReal = useSesion((estado) => estado.esReal)
  const { mensajes, enviando, usarProyecto, agregar, marcarValorada, setEnviando } = useConversacion()
  const borradorPendiente = useBorradorAsistente((estado) => estado.borrador)
  const proyectoInventario = useInventario((estado) => estado.proyecto)
  const iniciarInventario = useInventario((estado) => estado.iniciar)
  const [pregunta, setPregunta] = useState('')
  const final = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (proyecto) usarProyecto(proyecto)
  }, [proyecto, usarProyecto])

  // Los nombres del inventario, para enlazar los productos que nombra el Asistente. Sin red se
  // usan los guardados en el dispositivo; si no hay, el texto se muestra sin enlaces
  useEffect(() => {
    if (proyecto && proyectoInventario !== proyecto) void iniciarInventario(proyecto).catch(() => {})
  }, [proyecto, proyectoInventario, iniciarInventario])

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
        // Para que pueda decir "toca este botón" donde el operador está
        pantalla_actual: useNavegacion.getState().pantalla,
      })
      // Pidió registrar una venta: el Asistente la deja llenada en Ventas para que la confirme
      const items = respuesta.borrador?.items ?? []
      if (items.length > 0 && proyecto) {
        useBorradorAsistente.getState().poner(proyecto, items, respuesta.borrador?.para)
        verBorrador()
      }
      agregar({
        quienHabla: 'asistente',
        texto: respuesta.respuesta,
        acciones: items.length > 0 ? [] : respuesta.acciones,
        idRespuesta: respuesta.id_respuesta,
        conBorrador: items.length > 0,
        hecho:
          items.length > 0
            ? 'La orden está en Ventas, arriba. Hasta que toques «Guardar orden» no se guarda nada.'
            : hacerSolo(respuesta.acciones),
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

  const dictado = useDictado({
    alEscuchar: setPregunta,
    alTerminar: (texto) => void preguntar(texto),
  })

  const valorar = (indice: number, util: boolean) => {
    const mensaje = mensajes[indice]
    if (!mensaje.idRespuesta || mensaje.valorada) return
    marcarValorada(indice)
    // Si falla no pasa nada: la valoración es una ayuda, no una operación del negocio
    void pedir('POST', '/api/asistente/valoracion', { id_respuesta: mensaje.idRespuesta, util }).catch(
      () => {},
    )
  }

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
              <TextoConProductos texto={mensaje.texto} prefijo={prefijo} indice={indice} />
            </p>
            {mensaje.hecho && <Nota>{mensaje.hecho}</Nota>}
            {mensaje.conBorrador && borradorPendiente?.proyecto === proyecto && (
              <Boton aiId={`${prefijo}.ver-borrador-${indice}`} variante="secundario" onClick={verBorrador}>
                Revisar la orden por guardar
              </Boton>
            )}
            {mensaje.acciones?.map((accion) => {
              const destino = accion.pantalla
              if (!esPantalla(destino)) return null
              return (
                <Boton
                  key={destino}
                  aiId={`${prefijo}.accion-${indice}-${destino}`}
                  variante="secundario"
                  onClick={() => seguir(accion)}
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
        <div className={estilos.botonesPregunta}>
          {dictado.soportado && (
            <Boton
              aiId={`${prefijo}.hablar`}
              variante="secundario"
              deshabilitado={enviando && !dictado.escuchando}
              presionado={dictado.escuchando}
              onClick={dictado.escuchando ? dictado.detener : dictado.empezar}
            >
              {dictado.escuchando ? 'Listo, enviar' : 'Hablar'}
            </Boton>
          )}
          <Boton
            tipo="submit"
            aiId={`${prefijo}.enviar`}
            variante="ia"
            deshabilitado={enviando || dictado.escuchando || !pregunta.trim()}
          >
            Enviar pregunta
          </Boton>
        </div>
      </form>
      {dictado.escuchando && <Nota>Te escucho… habla y toca «Listo, enviar» al terminar.</Nota>}
      {dictado.aviso && <Nota>{dictado.aviso}</Nota>}
      {/* La voz no se puede seudonimizar: en un negocio real se avisa a dónde va (ADR-049) */}
      {dictado.soportado && esReal && (
        <Nota>Si hablas, tu navegador envía tu voz a Google o Microsoft para pasarla a texto.</Nota>
      )}
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
 * La ventana: el mismo Asistente junto a la pantalla de trabajo, y sigue abierta al cambiar
 * de pantalla. En pantalla ancha es una columna a la derecha que no tapa nada; en teléfono y
 * tablet es una hoja abajo que se achica a su barra para llenar los datos de atrás.
 */
export function AsistenteFlotante() {
  const irA = useNavegacion((estado) => estado.irA)
  const cerrar = useNavegacion((estado) => estado.cerrarAsistenteFlotante)
  const achicado = useNavegacion((estado) => estado.asistenteAchicado)
  const alternarAchicado = useNavegacion((estado) => estado.alternarAchicado)
  const [estado] = useEstadoAsistente()
  const panel = useRef<HTMLElement>(null)

  useEffect(() => {
    panel.current?.focus()
  }, [])

  const sinLlave = estado && !estado.listo && estado.puede_guardar_llave

  return (
    <section
      ref={panel}
      className={`${estilos.ventana} ${achicado ? estilos.achicada : ''}`}
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
          {/* Solo en la hoja de abajo: en la columna de la derecha no tapa nada */}
          <span className={estilos.soloHoja}>
            <Boton aiId="asistente-ventana.achicar" variante="discreto" onClick={alternarAchicado}>
              {achicado ? 'Agrandar' : 'Achicar'}
            </Boton>
          </span>
          {/* En el teléfono la hoja ya ocupa casi todo: el apartado completo sigue en el menú */}
          <span className={estilos.noEnTelefono}>
            <Boton aiId="asistente-ventana.ampliar" variante="discreto" onClick={() => irA('asistente')}>
              Pantalla completa
            </Boton>
          </span>
          <Boton aiId="asistente-ventana.cerrar" variante="discreto" onClick={cerrar}>
            Cerrar
          </Boton>
        </div>
      </header>
      {achicado ? null : sinLlave ? (
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
