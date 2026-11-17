import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { IDIOMA_DICTADO, useDictado } from './dictado'

/** Un reconocimiento de voz falso: el test decide qué "se escuchó" */
class ReconocimientoFalso {
  static ultimo: ReconocimientoFalso | null = null
  lang = ''
  interimResults = false
  continuous = true
  onresult: ((evento: unknown) => void) | null = null
  onerror: ((evento: { error: string }) => void) | null = null
  onend: (() => void) | null = null
  start = vi.fn()
  stop = vi.fn(() => this.onend?.())
  abort = vi.fn()
  constructor() {
    ReconocimientoFalso.ultimo = this
  }
  oir(texto: string, final: boolean) {
    const resultado = Object.assign([{ transcript: texto }], { isFinal: final })
    this.onresult?.({ resultIndex: 0, results: [resultado] })
  }
}

describe('hablarle al Asistente', () => {
  afterEach(() => {
    delete (window as unknown as Record<string, unknown>).webkitSpeechRecognition
  })

  it('sin dictado en el navegador, no se ofrece', () => {
    const { result } = renderHook(() => useDictado({ alEscuchar: vi.fn(), alTerminar: vi.fn() }))
    expect(result.current.soportado).toBe(false)
  })

  it('muestra lo que va entendiendo y envía el texto completo al terminar', () => {
    ;(window as unknown as Record<string, unknown>).webkitSpeechRecognition = ReconocimientoFalso
    const alEscuchar = vi.fn()
    const alTerminar = vi.fn()
    const { result } = renderHook(() => useDictado({ alEscuchar, alTerminar }))
    expect(result.current.soportado).toBe(true)

    act(() => result.current.empezar())
    const reconocimiento = ReconocimientoFalso.ultimo
    expect(reconocimiento?.lang).toBe(IDIOMA_DICTADO)
    expect(result.current.escuchando).toBe(true)

    act(() => reconocimiento?.oir('quiero registrar', false))
    expect(alEscuchar).toHaveBeenLastCalledWith('quiero registrar')
    act(() => reconocimiento?.oir('quiero registrar dos fideos', true))
    act(() => result.current.detener())

    expect(alTerminar).toHaveBeenCalledWith('quiero registrar dos fideos')
    expect(result.current.escuchando).toBe(false)
  })

  it('si no hay permiso de micrófono, lo dice con palabras', () => {
    ;(window as unknown as Record<string, unknown>).webkitSpeechRecognition = ReconocimientoFalso
    const alTerminar = vi.fn()
    const { result } = renderHook(() => useDictado({ alEscuchar: vi.fn(), alTerminar }))
    act(() => result.current.empezar())
    act(() => {
      ReconocimientoFalso.ultimo?.onerror?.({ error: 'not-allowed' })
      ReconocimientoFalso.ultimo?.onend?.()
    })
    expect(result.current.aviso).toMatch(/micrófono/)
    expect(alTerminar).not.toHaveBeenCalled()
  })
})
