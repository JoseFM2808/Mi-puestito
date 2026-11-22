import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type * as Cliente from '../../api/cliente'
import type { KardexCable } from '../../api/contrato'

const pedir = vi.fn()
vi.mock('../../api/cliente', async (original) => ({
  ...(await original<typeof Cliente>()),
  pedir: (...argumentos: unknown[]) => pedir(...argumentos),
}))

const { Kardex, mesPeruano } = await import('./Kardex')
const { SinConexion } = await import('../../api/cliente')
const { baseDe, cerrarBases } = await import('../../sincronizacion/base-local')
const { useSesion } = await import('../../stores/sesion')

const KARDEX: KardexCable = {
  mes: mesPeruano(),
  desde: '2026-11-01',
  hasta: '2026-11-22',
  no_disponibles: [],
  productos: [
    {
      nombre: 'Arroz',
      unidad: 'kg',
      inicial: '45.000',
      registrado: '0.000',
      compras: '20.000',
      vendido: '7.000',
      mermas: '0.000',
      ajustes: '0.000',
      final: '58.000',
    },
  ],
}

describe('kardex sin conexión', () => {
  beforeEach(async () => {
    cerrarBases()
    await baseDe('kardex-prueba').delete()
    cerrarBases()
    useSesion.setState({ proyecto: 'kardex-prueba' })
  })

  afterEach(() => {
    cleanup()
    pedir.mockReset()
  })

  it('con red lo guarda y sin red muestra lo guardado, diciendo de cuándo es', async () => {
    pedir.mockResolvedValue(KARDEX)
    render(<Kardex />)
    expect(await screen.findByText(/Arroz: quedan 58 kg/)).toBeTruthy()
    cleanup()
    await vi.waitFor(async () => expect(await baseDe('kardex-prueba').kardex.get(KARDEX.mes)).toBeTruthy())

    pedir.mockRejectedValue(new SinConexion())
    render(<Kardex />)
    expect(await screen.findByText(/Arroz: quedan 58 kg/)).toBeTruthy()
    expect(screen.getByText(/Sin conexión: es el cálculo guardado/)).toBeTruthy()
  })

  it('sin red y sin nada guardado, lo dice', async () => {
    pedir.mockRejectedValue(new SinConexion())
    render(<Kardex />)
    expect(await screen.findByText(/se ve cuando vuelva la conexión/)).toBeTruthy()
  })
})
