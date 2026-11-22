import { afterEach, describe, expect, it, vi } from 'vitest'
import { useSesion } from './sesion'

function responder(status: number, cuerpo: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve(new Response(JSON.stringify(cuerpo), { status }))),
  )
}

describe('ingreso: por qué no entró', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    useSesion.setState({ error: null, cargando: false })
  })

  it('PIN errado', async () => {
    responder(401, { detail: 'Usuario o PIN incorrecto' })
    expect(await useSesion.getState().iniciarSesion('anita', '1')).toBe(false)
    expect(useSesion.getState().error).toBe('Usuario o PIN incorrecto')
  })

  it('tras varios intentos dice que hay que esperar, con el tiempo del servidor', async () => {
    responder(429, { detail: 'Demasiados intentos con PIN incorrecto. Espera 30 segundos.' })
    await useSesion.getState().iniciarSesion('anita', '1')
    expect(useSesion.getState().error).toBe('Demasiados intentos con PIN incorrecto. Espera 30 segundos.')
  })

  it('un error del programa no se confunde con un PIN errado', async () => {
    responder(500, {})
    await useSesion.getState().iniciarSesion('anita', '1')
    expect(useSesion.getState().error).toMatch(/El programa tuvo un problema/)
  })
})
