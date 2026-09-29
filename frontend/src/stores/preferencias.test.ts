import { beforeEach, describe, expect, it } from 'vitest'
import { usePreferencias } from './preferencias'

describe('store de preferencias — tamaño de letra', () => {
  beforeEach(() => {
    usePreferencias.getState().cambiarTamanoLetra('normal')
    sessionStorage.clear()
  })

  it('arranca en Normal (sin atributo data-letra)', () => {
    expect(usePreferencias.getState().tamanoLetra).toBe('normal')
    expect(document.documentElement.dataset.letra).toBeUndefined()
  })

  it('al elegir "Muy grande" escribe data-letra en <html> y re-escala la UI', () => {
    usePreferencias.getState().cambiarTamanoLetra('muygrande')
    expect(document.documentElement.dataset.letra).toBe('muygrande')
  })

  it('persiste la elección en sessionStorage (dura la sesión del operador)', () => {
    usePreferencias.getState().cambiarTamanoLetra('grande')
    const guardado = sessionStorage.getItem('preferencias-operador')
    expect(guardado).not.toBeNull()
    expect(JSON.parse(guardado ?? '{}').state.tamanoLetra).toBe('grande')
  })

  it('volver a Normal quita el atributo data-letra', () => {
    usePreferencias.getState().cambiarTamanoLetra('muygrande')
    usePreferencias.getState().cambiarTamanoLetra('normal')
    expect(document.documentElement.dataset.letra).toBeUndefined()
  })
})
