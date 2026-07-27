import { useState } from 'react'
import { cabeceraAutorizacion } from '../../stores/sesion'
import './Asistente.css'

/**
 * Panel del Asistente (AI Companion). Chat simple: el operador escribe y
 * el Asistente responde con el mismo resumen que ve en el Dashboard, nunca
 * con datos de otro proyecto (lo garantiza el backend con el token).
 */

interface Mensaje {
  quienHabla: 'operador' | 'asistente'
  texto: string
}

export function Asistente() {
  const [mensajes, setMensajes] = useState<Mensaje[]>([
    {
      quienHabla: 'asistente',
      texto: 'Hola, soy tu Asistente. Puedes preguntarme sobre tu caja de hoy.',
    },
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
      const respuesta = await fetch('/api/asistente/preguntar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...cabeceraAutorizacion() },
        body: JSON.stringify({ mensaje: texto }),
      })
      const datos = await respuesta.json()
      const textoRespuesta = respuesta.ok
        ? datos.respuesta
        : (datos.detail ?? 'El Asistente no pudo responder ahora mismo.')
      setMensajes((actual) => [...actual, { quienHabla: 'asistente', texto: textoRespuesta }])
    } catch {
      setMensajes((actual) => [
        ...actual,
        {
          quienHabla: 'asistente',
          texto: 'No pude conectarme. Revisa tu conexión e intenta de nuevo.',
        },
      ])
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="asistente" data-ai-id="asistente">
      <div className="asistente-mensajes" role="log" aria-live="polite">
        {mensajes.map((mensaje, indice) => (
          <p
            key={indice}
            className={
              mensaje.quienHabla === 'asistente'
                ? 'asistente-burbuja asistente-burbuja-ia'
                : 'asistente-burbuja asistente-burbuja-operador'
            }
          >
            {mensaje.texto}
          </p>
        ))}
        {enviando && <p className="asistente-burbuja asistente-burbuja-ia">Pensando…</p>}
      </div>

      <form className="asistente-formulario" onSubmit={(evento) => void enviar(evento)}>
        <label className="campo-label" htmlFor="asistente-pregunta">
          Escríbele al Asistente
        </label>
        <input
          id="asistente-pregunta"
          className="campo-texto"
          data-ai-id="asistente.pregunta"
          type="text"
          placeholder="Por ejemplo: ¿cuánto vendí hoy?"
          value={pregunta}
          onChange={(evento) => setPregunta(evento.target.value)}
        />
        <button
          type="submit"
          className="btn btn-primario"
          data-ai-id="asistente.enviar"
          disabled={enviando}
        >
          Enviar
        </button>
      </form>
    </div>
  )
}
