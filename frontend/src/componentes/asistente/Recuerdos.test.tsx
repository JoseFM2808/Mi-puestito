import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const pedir = vi.fn()
vi.mock('../../api/cliente', async (original) => ({
  ...(await original<typeof import('../../api/cliente')>()),
  pedir: (...argumentos: unknown[]) => pedir(...argumentos),
}))

const { Recuerdos } = await import('./Recuerdos')
const { SinConexion } = await import('../../api/cliente')

describe('Lo que el Asistente recuerda (D-26)', () => {
  let guardados: { uuid: string; texto: string; creado_en: string }[]

  beforeEach(() => {
    guardados = [
      { uuid: 'a', texto: 'Sra. Rosa paga por Yape', creado_en: '2026-11-22T10:00:00Z' },
      { uuid: 'b', texto: 'Los sábados vendo menú', creado_en: '2026-11-22T11:00:00Z' },
    ]
    pedir.mockImplementation((metodo: string, ruta: string) => {
      if (metodo === 'GET') return Promise.resolve([...guardados])
      if (ruta === '/api/asistente/recuerdos') guardados = []
      else guardados = guardados.filter((r) => !ruta.endsWith(`/${r.uuid}`))
      return Promise.resolve(undefined)
    })
  })

  afterEach(() => {
    cleanup()
    pedir.mockReset()
  })

  it('muestra lo que recuerda y olvida uno por uno', async () => {
    render(<Recuerdos alCerrar={() => {}} />)
    expect(await screen.findByText('Sra. Rosa paga por Yape')).toBeTruthy()
    fireEvent.click(document.querySelector('[data-ai-id="asistente.olvidar-a"]')!)
    await waitFor(() => expect(screen.queryByText('Sra. Rosa paga por Yape')).toBeNull())
    expect(screen.getByText('Los sábados vendo menú')).toBeTruthy()
    expect(pedir).toHaveBeenCalledWith('DELETE', '/api/asistente/recuerdos/a')
  })

  it('olvidar todo pide confirmación', async () => {
    render(<Recuerdos alCerrar={() => {}} />)
    await screen.findByText('Los sábados vendo menú')
    fireEvent.click(screen.getByText('Olvidar todo'))
    expect(pedir).not.toHaveBeenCalledWith('DELETE', '/api/asistente/recuerdos')
    fireEvent.click(screen.getByText('Sí, olvidar todo'))
    expect(await screen.findByText('Todavía no recuerda nada.')).toBeTruthy()
  })

  it('sin conexión lo dice en palabras simples', async () => {
    pedir.mockRejectedValue(new SinConexion())
    render(<Recuerdos alCerrar={() => {}} />)
    expect(await screen.findByText(/No pude conectarme con el programa/)).toBeTruthy()
  })
})
