import { useState } from 'react'
import { ErrorApi, SinConexion, pedir } from '../../api/cliente'
import { useSesion } from '../../stores/sesion'
import { Aviso, Boton, Campo } from '../../ui/componentes'
import estilos from './Asistente.module.css'

/**
 * Panel del Asistente (AI Companion). Chat simple: el operador escribe y
 * el Asistente responde con el mismo resumen que ve en la Caja de hoy,
 * nunca con datos de otro proyecto (lo garantiza el backend con el token).
 *
 * Privacidad (ADR-034): el backend reemplaza los nombres de clientes y
 * proveedores antes de enviar la pregunta al servicio de IA externo. En un
 * negocio real se le dice al operador, en palabras simples.
 */

interface Mensaje {
  quienHabla: 'operador' | 'asistente'
  texto: string
}

export function Asistente() {
  const esReal = useSesion((estado) => estado.esReal)
  const [mensajes, setMensajes] = useState<Mensaje[]>([
    { quienHabla: 'asistente', texto: 'Hola, soy tu Asistente. Puedes preguntarme sobre tu caja de hoy.' },
  ])
  const [pregunta, setPregunta] = useState('')
  const [enviando, setEnviando] = useState(false)

  const enviar = async (evento: React.FormEvent) => {
    evento.preventDefault()
    const texto = pregunta.trim()
    if (!texto || enviando) return

    setMensajes((actual) => [...actual, { quienHabla: 'operador', texto }])
    setPregunta('')
    setEnviando(true)
    try {
      const { respuesta } = await pedir<{ respuesta: string }>('POST', '/api/asistente/preguntar', {
        mensaje: texto,
      })
      setMensajes((actual) => [...actual, { quienHabla: 'asistente', texto: respuesta }])
    } catch (error) {
      const texto =
        error instanceof SinConexion
          ? 'No pude conectarme. El Asistente necesita internet; lo demás de la app sigue funcionando.'
          : error instanceof ErrorApi
            ? error.detalle
            : 'El Asistente no pudo responder ahora mismo.'
      setMensajes((actual) => [...actual, { quienHabla: 'asistente', texto }])
    } finally {
      setEnviando(false)
    }
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
      <div className={estilos.mensajes} role="log" aria-live="polite">
        {mensajes.map((mensaje, indice) => (
          <p
            key={indice}
            className={`${estilos.burbuja} ${mensaje.quienHabla === 'asistente' ? estilos.burbujaIa : estilos.burbujaOperador}`}
          >
            {mensaje.texto}
          </p>
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
    </section>
  )
}
