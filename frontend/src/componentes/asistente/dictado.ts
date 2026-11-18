import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Hablarle al Asistente en vez de escribir (ADR-049), con el dictado del navegador (Web Speech
 * API). Chrome y Edge envían la voz a Google o Microsoft para pasarla a texto y necesitan
 * internet; en un negocio real la pantalla lo avisa. Firefox no lo tiene: ahí el botón no
 * aparece y se sigue escribiendo como siempre.
 *
 * Lo que se va entendiendo aparece en la caja de texto mientras se habla; al terminar, el
 * texto completo se envía como una pregunta escrita (y viaja seudonimizado, ADR-034).
 */

// Lo mínimo de la Web Speech API que se usa (TypeScript no la trae en lib.dom)
interface ResultadoReconocimiento {
  readonly isFinal: boolean
  readonly 0: { readonly transcript: string }
}
interface EventoReconocimiento {
  readonly resultIndex: number
  readonly results: ArrayLike<ResultadoReconocimiento>
}
interface Reconocimiento {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((evento: EventoReconocimiento) => void) | null
  onerror: ((evento: { error: string }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}
type ConstructorReconocimiento = new () => Reconocimiento

function constructorDelNavegador(): ConstructorReconocimiento | null {
  const ventana = window as unknown as {
    SpeechRecognition?: ConstructorReconocimiento
    webkitSpeechRecognition?: ConstructorReconocimiento
  }
  return ventana.SpeechRecognition ?? ventana.webkitSpeechRecognition ?? null
}

export const IDIOMA_DICTADO = 'es-PE'

const AVISOS: Record<string, string> = {
  'not-allowed':
    'El navegador no dejó usar el micrófono. Puedes permitirlo en el candado de la barra de direcciones.',
  'service-not-allowed': 'El navegador no dejó usar el micrófono.',
  'no-speech': 'No te escuché. Toca «Hablar» y habla cerca del teléfono o la tablet.',
  network: 'Para hablar hace falta internet. Puedes escribir tu pregunta.',
  'audio-capture': 'No encontré un micrófono en este equipo.',
}

export function useDictado({
  alEscuchar,
  alTerminar,
}: {
  /** Lo que se va entendiendo, para mostrarlo mientras se habla */
  alEscuchar: (texto: string) => void
  /** El texto completo al terminar de hablar */
  alTerminar: (texto: string) => void
}) {
  const [escuchando, setEscuchando] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const reconocimiento = useRef<Reconocimiento | null>(null)
  const textoFinal = useRef('')
  // Las funciones más recientes, sin reiniciar el reconocimiento en cada render
  const llamadas = useRef({ alEscuchar, alTerminar })
  llamadas.current = { alEscuchar, alTerminar }

  const soportado = constructorDelNavegador() !== null

  useEffect(() => () => reconocimiento.current?.abort(), [])

  const empezar = useCallback(() => {
    const Constructor = constructorDelNavegador()
    if (!Constructor || reconocimiento.current) return
    const nuevo = new Constructor()
    nuevo.lang = IDIOMA_DICTADO
    nuevo.interimResults = true
    nuevo.continuous = false
    textoFinal.current = ''
    nuevo.onresult = (evento) => {
      let provisional = ''
      for (let i = evento.resultIndex; i < evento.results.length; i += 1) {
        const resultado = evento.results[i]
        if (resultado.isFinal) textoFinal.current += resultado[0].transcript
        else provisional += resultado[0].transcript
      }
      llamadas.current.alEscuchar(`${textoFinal.current}${provisional}`.trim())
    }
    nuevo.onerror = (evento) => {
      if (evento.error !== 'aborted')
        setAviso(AVISOS[evento.error] ?? 'No pude escucharte. Puedes escribir tu pregunta.')
    }
    nuevo.onend = () => {
      reconocimiento.current = null
      setEscuchando(false)
      const texto = textoFinal.current.trim()
      if (texto) llamadas.current.alTerminar(texto)
    }
    reconocimiento.current = nuevo
    setAviso(null)
    setEscuchando(true)
    try {
      nuevo.start()
    } catch {
      reconocimiento.current = null
      setEscuchando(false)
      setAviso('No pude empezar a escuchar. Puedes escribir tu pregunta.')
    }
  }, [])

  /** Deja de escuchar y envía lo entendido hasta ahora */
  const detener = useCallback(() => reconocimiento.current?.stop(), [])

  return { soportado, escuchando, aviso, empezar, detener }
}
